import React, { useState, useRef, useEffect } from 'react';

const InputBox = ({ onSend, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  }, [input]);

  return (
    <div className="fixed bottom-8 left-[300px] right-0 z-50 flex justify-center pointer-events-none px-8">
      <div className="w-full max-w-3xl pointer-events-auto relative group">
        {/* Ambient Glow */}
        <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-secondary-container/20 to-primary/20 rounded-full blur-md opacity-50 group-focus-within:opacity-100 transition-opacity duration-300"></div>
        
        <div className="relative bg-surface-container-high/80 backdrop-blur-xl border border-outline-variant/50 rounded-full p-1.5 flex items-end shadow-2xl focus-within:border-primary/50 focus-within:bg-surface-container-highest/90 transition-all">
          {/* Attachment Button */}
          <button className="p-3 text-on-surface-variant hover:text-primary transition-colors flex-shrink-0 rounded-full hover:bg-white/5 mb-0.5">
            <span className="material-symbols-outlined text-[22px]">add_circle</span>
          </button>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            rows="1"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask anything about the lecture materials..."
            className="flex-1 bg-transparent border-none text-on-surface font-body-base focus:ring-0 resize-none py-3 px-2 max-h-32 placeholder:text-on-surface-variant/50 scrollbar-hide"
          />

          {/* Action Group */}
          <div className="flex items-center gap-1 p-1 mb-0.5 flex-shrink-0">
            <button className="p-2 text-on-surface-variant hover:text-primary transition-colors rounded-full hover:bg-white/5 hidden md:block">
              <span className="material-symbols-outlined text-[20px]">public</span>
            </button>
            
            {/* Send Button */}
            <button
              onClick={handleSend}
              disabled={disabled || !input.trim()}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ml-1 ${
                input.trim() && !disabled
                  ? 'bg-primary text-on-primary-fixed shadow-[0_0_15px_rgba(166,200,255,0.4)] hover:shadow-[0_0_20px_rgba(166,200,255,0.6)] hover:bg-primary-container'
                  : 'bg-surface-container text-on-surface-variant cursor-not-allowed'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]" data-weight="fill">arrow_upward</span>
            </button>
          </div>
        </div>

        {/* Helper Text */}
        <div className="text-center mt-3 text-[11px] text-on-surface-variant/60 font-body-sm">
          SemSaver Pro can synthesize across 4,000+ academic papers and your current semester syllabus.
        </div>
      </div>
    </div>
  );
};

export default InputBox;
