import React, { useState, useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import InputBox from './InputBox';

const ChatWindow = () => {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: "Hello! I'm your SemSaver assistant. Upload your syllabus or lecture notes, and I can help you synthesize concepts, find prerequisites, and prepare for exams. How can I help you today?",
      confidence: 1.0,
      sources: []
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingText]);

  const simulateStreaming = async (fullText, messageObj) => {
    setIsTyping(true);
    setStreamingText('');
    
    const words = fullText.split(' ');
    let currentText = '';
    
    for (let i = 0; i < words.length; i++) {
      currentText += (i === 0 ? '' : ' ') + words[i];
      setStreamingText(currentText);
      // Faster typing for longer texts, slower for short ones
      const delay = Math.max(20, 100 - (words.length / 5));
      await new Promise(resolve => setTimeout(resolve, delay));
    }
    
    setMessages(prev => [...prev, { ...messageObj, text: fullText }]);
    setStreamingText('');
    setIsTyping(false);
  };

  const handleSend = async (text) => {
    // Add user message
    const userMessage = { role: 'user', text };
    setMessages(prev => [...prev, userMessage]);

    try {
      setIsTyping(true);
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout

      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const data = await response.json();
      
      // Extract data from backend response
      const aiResponse = {
        role: 'assistant',
        text: data.answer,
        sources: data.sources || [],
        confidence: data.confidence
      };

      // Start streaming effect
      await simulateStreaming(data.answer, aiResponse);
    } catch (error) {
      console.error('Chat Error:', error);
      const msg = error.name === 'AbortError'
        ? "Request timed out after 30s. The backend is overloaded — try again."
        : "Error connecting to the AI engine. Please ensure the backend server is running.";
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `⚠️ ${msg}`,
        confidence: 0,
        sources: []
      }]);
      setIsTyping(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full relative overflow-hidden">
      {/* Header */}
      <header className="px-8 pb-6 pt-8 max-w-4xl mx-auto w-full flex items-center justify-between z-10">
        <div className="flex items-center gap-4">
          <span className="font-inter text-[12px] font-semibold text-primary border border-primary/30 bg-primary/10 px-3 py-1 rounded-full uppercase tracking-wider">STUDY HUB</span>
          <span className="text-on-surface-variant/60 text-xs font-mono uppercase tracking-widest">Active Index: Java_Course_V1</span>
        </div>
      </header>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-8 w-full max-w-4xl mx-auto flex flex-col pt-4 pb-32">
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
        
        {/* Streaming Message */}
        {streamingText && (
          <MessageBubble 
            message={{ 
              role: 'assistant', 
              text: streamingText, 
              sources: [], // Sources show up after streaming for simplicity
              confidence: 0.9 // Placeholder during streaming
            }} 
            isStreaming={true} 
          />
        )}

        {/* Loading Indicator */}
        {isTyping && !streamingText && (
          <div className="flex gap-4 max-w-[95%] opacity-40 grayscale animate-pulse">
            <div className="flex-shrink-0 mt-1">
              <div className="w-8 h-8 rounded-full border border-white/20 flex items-center justify-center">
                <span className="material-symbols-outlined text-white/50 text-[16px]">neurology</span>
              </div>
            </div>
            <div className="glass-panel rounded-2xl rounded-tl-sm p-4 w-32 border border-white/5">
              <div className="flex gap-1.5 items-center">
                <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 rounded-full bg-primary/40 animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={chatEndRef} />
      </div>

      {/* Input Area */}
      <InputBox onSend={handleSend} disabled={isTyping} />
    </div>
  );
};

export default ChatWindow;
