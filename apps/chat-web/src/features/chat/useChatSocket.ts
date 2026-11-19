import { useEffect, useRef, useState } from 'react';

import type { ChatMessage } from '../../lib/api';

export type SocketStatus = 'connecting' | 'online' | 'reconnecting' | 'offline';

interface Options {
  url: string | null;
  onMessage: (message: ChatMessage) => void;
  /** Called when a socket reopens after a drop, so the caller can catch up. */
  onReconnect?: () => void;
  onStatusChange?: (status: SocketStatus) => void;
}

const INITIAL_DELAY_MS = 1_000;
const MAX_DELAY_MS = 30_000;

/**
 * One socket for the session, with exponential backoff (1s → 30s).
 * Frames we do not understand are ignored: the socket must stay useful for
 * the next event rather than die on one bad frame.
 */
export function useChatSocket({ url, onMessage, onReconnect, onStatusChange }: Options) {
  const [status, setStatus] = useState<SocketStatus>(url ? 'connecting' : 'offline');
  const handlers = useRef({ onMessage, onReconnect, onStatusChange });
  handlers.current = { onMessage, onReconnect, onStatusChange };

  useEffect(() => {
    if (!url) {
      setStatus('offline');
      return;
    }

    let socket: WebSocket | null = null;
    let attempt = 0;
    let timer: number | undefined;
    let disposed = false;
    let connectedBefore = false;

    const update = (next: SocketStatus) => {
      if (disposed) return;
      setStatus(next);
      handlers.current.onStatusChange?.(next);
    };

    const connect = () => {
      update(attempt === 0 ? 'connecting' : 'reconnecting');
      socket = new WebSocket(url);

      socket.onopen = () => {
        if (disposed) return;
        attempt = 0;
        update('online');
        if (connectedBefore) handlers.current.onReconnect?.();
        connectedBefore = true;
      };

      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(String(event.data)) as {
            type?: string;
            message?: ChatMessage;
          };
          if (payload.type === 'message.created' && payload.message) {
            handlers.current.onMessage(payload.message);
          }
        } catch {
          // ignore frames we cannot parse
        }
      };

      socket.onclose = () => {
        if (disposed) return;
        // Still retrying, so the UI says "reconnecting", not "offline".
        update('reconnecting');
        const delay = Math.min(MAX_DELAY_MS, INITIAL_DELAY_MS * 2 ** attempt);
        attempt += 1;
        timer = window.setTimeout(connect, delay);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      disposed = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [url]);

  return status;
}
