import React from 'react';
import { useStore } from '../store';

export const MessagesPanel: React.FC = () => {
  const { messages } = useStore();

  return (
    <div className="messages-panel">
      <div className="messages-header">Messages</div>
      <div className="messages-content">
        {messages.map(msg => (
          <div key={msg.id} className={`message ${msg.type}`}>
            <span className="msg-time">[{msg.time}]</span>
            <span className="msg-type">{msg.type.toUpperCase()}:</span>
            <span className="msg-text">{msg.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
