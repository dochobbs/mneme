import { useState, useEffect, useRef } from 'react';
import { X, Send, User, Stethoscope, Loader2, AlertCircle } from 'lucide-react';
import { PatientDetail } from '../lib/api';
import { useSyrinxSession, ChatMessage } from '../hooks/useSyrinxSession';
import { buildScenario, ParentPersona } from '../lib/roleplay';

interface RolePlayModalProps {
  patientData: PatientDetail;
  chiefComplaint: string;
  parentPersona: ParentPersona;
  onClose: () => void;
}

export default function RolePlayModal({
  patientData,
  chiefComplaint,
  parentPersona,
  onClose,
}: RolePlayModalProps) {
  const { patient } = patientData;
  const fullName = `${patient.given_names.join(' ')} ${patient.family_name}`;

  const {
    messages,
    isConnected,
    isConnecting,
    isWaitingForResponse,
    error,
    connect,
    sendMessage,
    disconnect,
    clearError,
  } = useSyrinxSession();

  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Connect to Syrinx on mount
  useEffect(() => {
    const scenario = buildScenario(patientData, chiefComplaint, parentPersona);
    connect(scenario);

    return () => {
      disconnect();
    };
  }, []);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input when connected
  useEffect(() => {
    if (isConnected && !isWaitingForResponse) {
      inputRef.current?.focus();
    }
  }, [isConnected, isWaitingForResponse]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim() || isWaitingForResponse || !isConnected) return;

    sendMessage(inputValue.trim());
    setInputValue('');
  };

  const handleEndSession = () => {
    disconnect();
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Header */}
      <header
        className="flex items-center justify-between px-6 py-4 flex-shrink-0"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="flex items-center">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center mr-3"
            style={{ backgroundColor: 'var(--accent-light)' }}
          >
            <span className="text-sm font-medium" style={{ color: 'var(--accent)' }}>
              {patient.given_names[0]?.[0]}{patient.family_name[0]}
            </span>
          </div>
          <div>
            <h2 className="font-display font-semibold" style={{ color: 'var(--text-primary)' }}>
              {fullName}
            </h2>
            <p className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
              {chiefComplaint}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {isConnected && (
            <span
              className="text-xs px-2 py-1 rounded-full"
              style={{
                backgroundColor: 'rgba(45, 106, 79, 0.1)',
                color: 'var(--clinical-success)',
              }}
            >
              Connected
            </span>
          )}
          <button
            onClick={handleEndSession}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-secondary)',
            }}
          >
            End Session
          </button>
          <button
            onClick={handleEndSession}
            className="p-1 rounded-lg transition-colors"
            style={{ color: 'var(--text-tertiary)' }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bg-secondary)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-auto p-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Connecting State */}
          {isConnecting && (
            <div className="flex items-center justify-center py-8">
              <Loader2
                className="w-6 h-6 animate-spin mr-3"
                style={{ color: 'var(--accent)' }}
              />
              <span style={{ color: 'var(--text-secondary)' }}>
                Connecting to simulation...
              </span>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div
              className="flex items-center p-4 rounded-lg"
              style={{
                backgroundColor: 'rgba(155, 44, 44, 0.1)',
                border: '1px solid rgba(155, 44, 44, 0.2)',
              }}
            >
              <AlertCircle className="w-5 h-5 mr-3" style={{ color: 'var(--clinical-error)' }} />
              <div className="flex-1">
                <p className="text-sm font-medium" style={{ color: 'var(--clinical-error)' }}>
                  Connection Error
                </p>
                <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                  {error}
                </p>
              </div>
              <button
                onClick={clearError}
                className="text-sm underline"
                style={{ color: 'var(--text-tertiary)' }}
              >
                Dismiss
              </button>
            </div>
          )}

          {/* Messages */}
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}

          {/* Typing Indicator */}
          {isWaitingForResponse && (
            <div className="flex gap-3">
              <div
                className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                style={{
                  backgroundColor: 'rgba(115, 140, 130, 0.15)',
                  color: 'var(--accent-tertiary)',
                }}
              >
                <User className="w-4 h-4" />
              </div>
              <div
                className="px-4 py-3 rounded-2xl rounded-tl-sm"
                style={{ backgroundColor: 'var(--bg-secondary)' }}
              >
                <div className="flex gap-1">
                  <span
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: '0ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: '150ms' }}
                  />
                  <span
                    className="w-2 h-2 rounded-full animate-bounce"
                    style={{ backgroundColor: 'var(--text-tertiary)', animationDelay: '300ms' }}
                  />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <footer
        className="flex-shrink-0 px-6 py-4"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderTop: '1px solid var(--border)',
        }}
      >
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-3">
          <input
            ref={inputRef}
            type="text"
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder={isConnected ? "Type your response as the doctor..." : "Connecting..."}
            className="flex-1 px-4 py-3 rounded-lg text-sm"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border)',
              color: 'var(--text-primary)',
            }}
            disabled={!isConnected || isWaitingForResponse}
          />
          <button
            type="submit"
            className="px-4 py-3 rounded-lg transition-colors flex items-center"
            style={{
              backgroundColor: 'var(--accent)',
              color: 'var(--text-inverse)',
              opacity: !inputValue.trim() || !isConnected || isWaitingForResponse ? 0.6 : 1,
            }}
            disabled={!inputValue.trim() || !isConnected || isWaitingForResponse}
          >
            <Send className="w-5 h-5" />
          </button>
        </form>
      </footer>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isDoctor = message.speaker === 'doctor';

  return (
    <div className={`flex gap-3 ${isDoctor ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
        style={{
          backgroundColor: isDoctor ? 'var(--accent-light)' : 'rgba(115, 140, 130, 0.15)',
          color: isDoctor ? 'var(--accent)' : 'var(--accent-tertiary)',
        }}
      >
        {isDoctor ? <Stethoscope className="w-4 h-4" /> : <User className="w-4 h-4" />}
      </div>

      {/* Message */}
      <div className={`max-w-[75%] ${isDoctor ? 'text-right' : ''}`}>
        <span
          className="text-xs font-medium block mb-1"
          style={{ color: isDoctor ? 'var(--accent)' : 'var(--text-tertiary)' }}
        >
          {isDoctor ? 'You (Doctor)' : 'Parent'}
        </span>
        <div
          className={`px-4 py-3 rounded-2xl ${isDoctor ? 'rounded-tr-sm' : 'rounded-tl-sm'}`}
          style={{
            backgroundColor: isDoctor ? 'var(--accent-light)' : 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          }}
        >
          <p className="text-sm whitespace-pre-wrap">{message.text}</p>
        </div>
        <span
          className="text-xs block mt-1"
          style={{ color: 'var(--text-tertiary)' }}
        >
          {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </div>
  );
}
