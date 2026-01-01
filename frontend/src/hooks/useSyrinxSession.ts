import { useState, useRef, useCallback, useEffect } from 'react';

const SYRINX_WS_URL = 'ws://localhost:8003/api/session';

export interface ChatMessage {
  id: string;
  speaker: 'doctor' | 'parent';
  text: string;
  timestamp: Date;
}

export interface SyrinxScenario {
  description: string;
  patient: {
    name: string;
    age: string;
    sex: string;
    allergies: string[];
    medications: string[];
    chronic_conditions: string[];
  };
  parent: {
    style: string;
  };
  chief_complaint: string;
}

interface SyrinxMessage {
  type: 'init' | 'message' | 'error' | 'end' | 'connected';
  text?: string;
  error?: string;
}

export function useSyrinxSession() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const messageIdRef = useRef(0);

  const generateId = () => {
    messageIdRef.current += 1;
    return `msg-${messageIdRef.current}`;
  };

  const connect = useCallback((scenario: SyrinxScenario) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setError(null);
    setMessages([]);

    const ws = new WebSocket(SYRINX_WS_URL);

    ws.onopen = () => {
      setIsConnecting(false);
      setIsConnected(true);
      setIsWaitingForResponse(true);

      // Send init message with role and scenario
      ws.send(JSON.stringify({
        type: 'init',
        role: 'doctor',
        scenario,
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data: SyrinxMessage = JSON.parse(event.data);

        if (data.type === 'message' && data.text) {
          const messageText = data.text;
          setMessages(prev => [...prev, {
            id: generateId(),
            speaker: 'parent',
            text: messageText,
            timestamp: new Date(),
          }]);
          setIsWaitingForResponse(false);
        } else if (data.type === 'error') {
          setError(data.error || 'An error occurred');
          setIsWaitingForResponse(false);
        } else if (data.type === 'end') {
          setIsConnected(false);
        }
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = () => {
      setError('Connection error. Is Syrinx running on port 8003?');
      setIsConnecting(false);
      setIsConnected(false);
      setIsWaitingForResponse(false);
    };

    ws.onclose = () => {
      setIsConnected(false);
      setIsConnecting(false);
      setIsWaitingForResponse(false);
    };

    wsRef.current = ws;
  }, []);

  const sendMessage = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected to Syrinx');
      return;
    }

    // Add user message immediately
    setMessages(prev => [...prev, {
      id: generateId(),
      speaker: 'doctor',
      text,
      timestamp: new Date(),
    }]);

    // Send to server
    setIsWaitingForResponse(true);
    wsRef.current.send(JSON.stringify({
      type: 'message',
      text,
    }));
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
    setIsWaitingForResponse(false);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return {
    messages,
    isConnected,
    isConnecting,
    isWaitingForResponse,
    error,
    connect,
    sendMessage,
    disconnect,
    clearError,
  };
}
