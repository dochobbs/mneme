import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, MailOpen, User, Clock } from 'lucide-react';
import { format } from 'date-fns';
import { getMessages, markMessageRead, Message } from '../lib/api';

export default function Messages() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedMessage, setSelectedMessage] = useState<Message | null>(null);
  const [filter, setFilter] = useState<'all' | 'unread'>('all');

  useEffect(() => {
    loadMessages();
  }, [filter]);

  async function loadMessages() {
    try {
      setLoading(true);
      const data = await getMessages(100, filter === 'unread');
      setMessages(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectMessage(msg: Message) {
    setSelectedMessage(msg);
    if (!msg.is_read) {
      try {
        await markMessageRead(msg.id);
        setMessages(prev =>
          prev.map(m => m.id === msg.id ? { ...m, is_read: true } : m)
        );
      } catch (err) {
        console.error('Failed to mark as read:', err);
      }
    }
  }

  function getCategoryStyle(category?: string): { bg: string; color: string } {
    switch (category) {
      case 'refill-request': return { bg: 'rgba(122, 163, 148, 0.15)', color: 'var(--accent-secondary)' };
      case 'clinical-question': return { bg: 'rgba(45, 90, 74, 0.1)', color: 'var(--accent)' };
      case 'appointment-request': return { bg: 'rgba(45, 106, 79, 0.1)', color: 'var(--clinical-success)' };
      case 'lab-result-question': return { bg: 'rgba(198, 112, 48, 0.1)', color: 'var(--clinical-warning)' };
      default: return { bg: 'var(--bg-secondary)', color: 'var(--text-secondary)' };
    }
  }

  return (
    <div className="h-full flex">
      {/* Message list */}
      <div
        className="w-96 flex flex-col"
        style={{
          backgroundColor: 'var(--bg-card)',
          borderRight: '1px solid var(--border)'
        }}
      >
        <div className="p-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <h1 className="text-xl font-display font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
            Messages
          </h1>
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className="px-3 py-1 text-sm rounded-full transition-colors"
              style={{
                backgroundColor: filter === 'all' ? 'var(--accent-light)' : 'transparent',
                color: filter === 'all' ? 'var(--accent)' : 'var(--text-secondary)'
              }}
            >
              All
            </button>
            <button
              onClick={() => setFilter('unread')}
              className="px-3 py-1 text-sm rounded-full transition-colors"
              style={{
                backgroundColor: filter === 'unread' ? 'var(--accent-light)' : 'transparent',
                color: filter === 'unread' ? 'var(--accent)' : 'var(--text-secondary)'
              }}
            >
              Unread
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-auto">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div
                className="w-6 h-6 border-2 rounded-full animate-spin"
                style={{
                  borderColor: 'var(--accent-light)',
                  borderTopColor: 'var(--accent)'
                }}
              />
            </div>
          )}

          {error && (
            <div className="p-4 text-sm" style={{ color: 'var(--clinical-error)' }}>
              {error}
            </div>
          )}

          {!loading && !error && messages.length === 0 && (
            <div className="text-center py-8" style={{ color: 'var(--text-secondary)' }}>
              <Mail className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--text-tertiary)' }} />
              <p>No messages</p>
            </div>
          )}

          {!loading && !error && messages.map(msg => (
            <div
              key={msg.id}
              onClick={() => handleSelectMessage(msg)}
              className="p-4 cursor-pointer transition-colors"
              style={{
                borderBottom: '1px solid var(--border-light)',
                backgroundColor: selectedMessage?.id === msg.id
                  ? 'var(--accent-light)'
                  : !msg.is_read
                    ? 'rgba(45, 90, 74, 0.05)'
                    : 'transparent'
              }}
              onMouseEnter={e => {
                if (selectedMessage?.id !== msg.id) {
                  e.currentTarget.style.backgroundColor = 'var(--bg-secondary)';
                }
              }}
              onMouseLeave={e => {
                e.currentTarget.style.backgroundColor = selectedMessage?.id === msg.id
                  ? 'var(--accent-light)'
                  : !msg.is_read
                    ? 'rgba(45, 90, 74, 0.05)'
                    : 'transparent';
              }}
            >
              <div className="flex items-start gap-3">
                {msg.is_read ? (
                  <MailOpen className="w-5 h-5 mt-0.5" style={{ color: 'var(--text-tertiary)' }} />
                ) : (
                  <Mail className="w-5 h-5 mt-0.5" style={{ color: 'var(--accent)' }} />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <span
                      className="font-medium truncate"
                      style={{ color: !msg.is_read ? 'var(--text-primary)' : 'var(--text-secondary)' }}
                    >
                      {msg.patient_name || msg.sender_name}
                    </span>
                    <span className="text-xs ml-2" style={{ color: 'var(--text-tertiary)' }}>
                      {format(new Date(msg.sent_datetime), 'MMM d')}
                    </span>
                  </div>
                  {msg.subject && (
                    <p className="text-sm truncate" style={{ color: 'var(--text-secondary)' }}>
                      {msg.subject}
                    </p>
                  )}
                  <p className="text-sm truncate mt-1" style={{ color: 'var(--text-tertiary)' }}>
                    {msg.message_body.slice(0, 60)}...
                  </p>
                  {msg.category && (
                    <span
                      className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full"
                      style={getCategoryStyle(msg.category)}
                    >
                      {msg.category.replace(/-/g, ' ')}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Message detail */}
      <div className="flex-1 flex flex-col" style={{ backgroundColor: 'var(--bg-secondary)' }}>
        {selectedMessage ? (
          <>
            <div className="p-6" style={{ backgroundColor: 'var(--bg-card)', borderBottom: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center"
                    style={{ backgroundColor: 'var(--accent-light)' }}
                  >
                    <User className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                  </div>
                  <div>
                    <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>
                      {selectedMessage.sender_name}
                    </h2>
                    <button
                      onClick={() => navigate(`/patients/${selectedMessage.patient_id}`)}
                      className="text-sm transition-colors"
                      style={{ color: 'var(--accent)' }}
                      onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
                      onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
                    >
                      View Patient
                    </button>
                  </div>
                </div>
                <div className="flex items-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
                  <Clock className="w-4 h-4 mr-1" />
                  {format(new Date(selectedMessage.sent_datetime), 'MMM d, yyyy h:mm a')}
                </div>
              </div>
              {selectedMessage.subject && (
                <h3 className="text-lg font-display font-medium" style={{ color: 'var(--text-primary)' }}>
                  {selectedMessage.subject}
                </h3>
              )}
            </div>

            <div className="flex-1 overflow-auto p-6">
              <div className="card p-4 mb-4">
                <p className="whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                  {selectedMessage.message_body}
                </p>
              </div>

              {selectedMessage.reply_body && (
                <div
                  className="rounded-lg p-4"
                  style={{
                    backgroundColor: 'var(--accent-light)',
                    border: '1px solid rgba(45, 90, 74, 0.2)'
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--accent)' }}>
                      Reply from {selectedMessage.replier_name || 'Staff'}
                    </span>
                    {selectedMessage.replier_role && (
                      <span className="text-xs" style={{ color: 'var(--accent-secondary)' }}>
                        ({selectedMessage.replier_role})
                      </span>
                    )}
                  </div>
                  <p className="whitespace-pre-wrap" style={{ color: 'var(--text-secondary)' }}>
                    {selectedMessage.reply_body}
                  </p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center" style={{ color: 'var(--text-tertiary)' }}>
            <div className="text-center">
              <Mail className="w-12 h-12 mx-auto mb-4" style={{ color: 'var(--text-tertiary)' }} />
              <p>Select a message to read</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
