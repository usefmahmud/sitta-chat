import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';

import { Composer } from '../features/chat/Composer';
import { ConversationList } from '../features/chat/ConversationList';
import { Thread } from '../features/chat/Thread';
import { useChatSocket, type SocketStatus } from '../features/chat/useChatSocket';
import { ApiError, type ChatMessage, type Conversation } from '../lib/api';
import {
  isNearBottom,
  mergeMessages,
  nextSeq,
  type UiMessage,
} from '../lib/messages';
import { useSession } from '../session/SessionProvider';

const PAGE_SIZE = 30;

function newClientId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID();
  }
  return `c-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export default function ChatPage() {
  const { api, token, user, signOut } = useSession();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [listState, setListState] = useState<'loading' | 'ready' | 'error'>('loading');
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [threadState, setThreadState] = useState<'idle' | 'loading' | 'ready' | 'error'>(
    'idle',
  );
  const [hasMore, setHasMore] = useState(false);
  const [nextBefore, setNextBefore] = useState<number | null>(null);
  const [unread, setUnread] = useState<Record<string, number>>({});
  const [showPill, setShowPill] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<SocketStatus>('connecting');

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const activeIdRef = useRef<string | null>(null);
  const messagesRef = useRef<UiMessage[]>([]);
  const loadingOlderRef = useRef(false);

  activeIdRef.current = activeId;
  messagesRef.current = messages;

  const scrollToBottom = useCallback(() => {
    const element = scrollRef.current;
    if (element) element.scrollTop = element.scrollHeight;
  }, []);

  const refreshConversations = useCallback(async () => {
    try {
      const list = await api.listConversations();
      setConversations(list);
      setListState('ready');
    } catch {
      setListState('error');
    }
  }, [api]);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  const openConversation = useCallback(
    async (conversationId: string) => {
      setActiveId(conversationId);
      setUnread((current) => ({ ...current, [conversationId]: 0 }));
      setThreadState('loading');
      setMessages([]);
      setShowPill(false);
      setHasMore(false);
      setNextBefore(null);

      try {
        const page = await api.listMessages(conversationId, { limit: PAGE_SIZE });
        setMessages(mergeMessages([], page.items));
        setHasMore(page.has_more);
        setNextBefore(page.next_before_seq);
        setThreadState('ready');
        requestAnimationFrame(scrollToBottom);
      } catch {
        setThreadState('error');
      }
    },
    [api, scrollToBottom],
  );

  const loadOlder = useCallback(async () => {
    const conversationId = activeIdRef.current;
    const cursor = nextBefore;
    const element = scrollRef.current;
    if (!conversationId || cursor == null || loadingOlderRef.current || !element) return;

    loadingOlderRef.current = true;
    const previousHeight = element.scrollHeight;
    try {
      const page = await api.listMessages(conversationId, {
        beforeSeq: cursor,
        limit: PAGE_SIZE,
      });
      setMessages((current) => mergeMessages(current, page.items));
      setHasMore(page.has_more);
      setNextBefore(page.next_before_seq);
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight - previousHeight;
        }
      });
    } catch {
      // keep what we have; the button can be pressed again
    } finally {
      loadingOlderRef.current = false;
    }
  }, [api, nextBefore]);

  const handleScroll = useCallback(() => {
    const element = scrollRef.current;
    if (!element) return;
    if (isNearBottom(element)) setShowPill(false);
    if (element.scrollTop < 80) void loadOlder();
  }, [loadOlder]);

  const handleIncoming = useCallback((message: ChatMessage) => {
    const isActive = message.conversation_id === activeIdRef.current;

    setConversations((current) =>
      current.map((conversation) =>
        conversation.id === message.conversation_id
          ? {
              ...conversation,
              last_message_at: message.created_at,
              last_message_preview: message.body,
            }
          : conversation,
      ),
    );

    if (!isActive) {
      setUnread((current) => ({
        ...current,
        [message.conversation_id]: (current[message.conversation_id] ?? 0) + 1,
      }));
      return;
    }

    const element = scrollRef.current;
    setMessages((current) => mergeMessages(current, [message]));
    if (element && isNearBottom(element)) {
      requestAnimationFrame(scrollToBottom);
    } else {
      setShowPill(true);
    }
  }, [scrollToBottom]);

  const catchUp = useCallback(async () => {
    const conversationId = activeIdRef.current;
    void refreshConversations();
    if (!conversationId) return;

    const lastSeq = messagesRef.current.reduce(
      (max, message) => (message.seq > max ? message.seq : max),
      0,
    );
    if (lastSeq === 0) return;

    try {
      const page = await api.listMessages(conversationId, {
        afterSeq: lastSeq,
        limit: 100,
      });
      if (page.items.length > 0) {
        setMessages((current) => mergeMessages(current, page.items));
        requestAnimationFrame(scrollToBottom);
      }
    } catch {
      // the next reconnect will try again
    }
  }, [api, refreshConversations, scrollToBottom]);

  useChatSocket({
    url: token ? api.socketUrl(token) : null,
    onMessage: handleIncoming,
    onReconnect: () => void catchUp(),
    onStatusChange: setConnectionStatus,
  });

  const send = useCallback(
    async (body: string): Promise<boolean> => {
      const conversationId = activeIdRef.current;
      if (!conversationId) return false;

      const clientMsgId = newClientId();
      const optimistic: UiMessage = {
        id: `local-${clientMsgId}`,
        conversation_id: conversationId,
        sender_id: user?.id ?? '',
        seq: nextSeq(messagesRef.current),
        body,
        client_msg_id: clientMsgId,
        created_at: new Date().toISOString(),
        status: 'sending',
      };

      setMessages((current) => mergeMessages(current, [optimistic]));
      requestAnimationFrame(scrollToBottom);

      try {
        const saved = await api.sendMessage(conversationId, { body, clientMsgId });
        setMessages((current) =>
          mergeMessages(
            current.filter((message) => message.id !== optimistic.id),
            [{ ...saved, status: 'sent' }],
          ),
        );
        setConversations((current) =>
          current.map((conversation) =>
            conversation.id === conversationId
              ? {
                  ...conversation,
                  last_message_at: saved.created_at,
                  last_message_preview: saved.body,
                }
              : conversation,
          ),
        );
        requestAnimationFrame(scrollToBottom);
        return true;
      } catch (error) {
        if (error instanceof ApiError && error.status === 0) {
          setMessages((current) =>
            mergeMessages(
              current.map((message) =>
                message.id === optimistic.id ? { ...message, status: 'failed' } : message,
              ),
              [],
            ),
          );
        } else {
          setMessages((current) =>
            mergeMessages(
              current.map((message) =>
                message.id === optimistic.id ? { ...message, status: 'failed' } : message,
              ),
              [],
            ),
          );
        }
        return false;
      }
    },
    [api, scrollToBottom, user?.id],
  );

  const retry = useCallback(
    (message: UiMessage) => {
      if (!message.client_msg_id) return;
      const conversationId = message.conversation_id;
      setMessages((current) =>
        mergeMessages(
          current.map((item) =>
            item.id === message.id ? { ...item, status: 'sending' } : item,
          ),
          [],
        ),
      );

      void api
        .sendMessage(conversationId, {
          body: message.body,
          clientMsgId: message.client_msg_id,
        })
        .then((saved) => {
          setMessages((current) =>
            mergeMessages(
              current.filter((item) => item.id !== message.id),
              [{ ...saved, status: 'sent' }],
            ),
          );
        })
        .catch(() => {
          setMessages((current) =>
            mergeMessages(
              current.map((item) =>
                item.id === message.id ? { ...item, status: 'failed' } : item,
              ),
              [],
            ),
          );
        });
    },
    [api],
  );

  useLayoutEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    if (isNearBottom(element)) element.scrollTop = element.scrollHeight;
  }, [messages.length]);

  const activeConversation =
    conversations.find((conversation) => conversation.id === activeId) ?? null;

  return (
    <main className="mx-auto flex h-screen w-full max-w-6xl flex-col overflow-hidden bg-white shadow-sm md:flex-row">
      <div className={activeId ? 'hidden h-full md:flex' : 'flex h-full'}>
        <ConversationList
          conversations={conversations}
          activeId={activeId}
          unread={unread}
          status={listState}
          connectionStatus={connectionStatus}
          onSelect={(id) => void openConversation(id)}
          onRetry={() => void refreshConversations()}
          onSignOut={signOut}
        />
      </div>

      <div className={activeId ? 'flex h-full min-w-0 flex-1 flex-col' : 'hidden h-full min-w-0 flex-1 flex-col md:flex'}>
        <Thread
          conversation={activeConversation}
          messages={messages}
          viewerId={user?.id ?? ''}
          state={threadState}
          hasMore={hasMore}
          showPill={showPill}
          scrollRef={scrollRef}
          onScroll={handleScroll}
          onLoadOlder={() => void loadOlder()}
          onJumpLatest={() => {
            scrollToBottom();
            setShowPill(false);
          }}
          onRetryMessage={retry}
          onBack={() => setActiveId(null)}
          onRetryLoad={() => {
            if (activeId) void openConversation(activeId);
          }}
        />
        {activeId ? <Composer disabled={connectionStatus === 'offline'} onSend={send} /> : null}
      </div>

    </main>
  );
}
