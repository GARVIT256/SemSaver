import React from 'react';

const MessageBubble = ({ message, isStreaming = false }) => {
  const { role, text, sources, confidence } = message;
  const isAi = role === 'assistant' || role === 'bot';

  if (!isAi) {
    return (
      <div className="flex justify-end mb-8">
        <div className="max-w-[80%] bg-surface-container-high rounded-2xl rounded-tr-sm px-5 py-4 border border-outline-variant/30 text-on-surface font-body-base text-body-base shadow-sm">
          {text}
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 max-w-[95%] mb-8">
      {/* AI Avatar */}
      <div className="flex-shrink-0 mt-1">
        <div className="w-8 h-8 rounded-full bg-gradient-to-b from-primary-container to-secondary-container flex items-center justify-center shadow-[0_0_10px_rgba(79,157,255,0.3)]">
          <span className="material-symbols-outlined text-white text-[16px]">neurology</span>
        </div>
      </div>

      {/* AI Card */}
      <div className="glass-panel rounded-2xl rounded-tl-sm p-6 w-full glow-border relative overflow-hidden group">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-50"></div>
        
        {/* Meta Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className="font-mono-label text-mono-label text-primary-fixed">SemSaver V4 (Deep Context)</span>
            {sources && sources.length > 0 && (
              <>
                <span className="text-on-surface-variant text-[12px]">•</span>
                <span className="text-on-surface-variant text-[12px]">Synthesizing {sources.length} sources</span>
              </>
            )}
          </div>
          
          {/* Confidence Bar */}
          {confidence !== undefined && (
            <div className="flex items-center gap-2 bg-surface-container/50 px-2.5 py-1 rounded-md border border-white/5" title="Retrieval Confidence Score">
              <span className="text-[11px] text-on-surface-variant font-mono">CONF:</span>
              <div className="w-16 h-1.5 bg-surface-variant rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-primary to-tertiary-container transition-all duration-500" 
                  style={{ width: `${confidence * 100}%` }}
                ></div>
              </div>
              <span className="text-[11px] text-primary font-bold">{Math.round(confidence * 100)}%</span>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="font-body-base text-body-base text-on-background leading-relaxed space-y-4">
          <div className="whitespace-pre-wrap">
            {text}
            {isStreaming && (
              <span className="inline-block w-2 h-4 bg-primary align-middle ml-1 cursor-blink"></span>
            )}
          </div>
        </div>

        {/* Footer / Sources */}
        {sources && sources.length > 0 && (
          <div className="mt-6 pt-4 border-t border-white/10 flex items-center justify-between">
            <div className="flex -space-x-2">
              {sources.map((source, idx) => (
                <div 
                  key={idx}
                  className="w-8 h-8 rounded-full bg-surface-container border border-outline-variant flex items-center justify-center text-xs font-mono text-primary z-30 shadow-sm cursor-pointer hover:-translate-y-1 transition-transform"
                  title={source}
                >
                  [{idx + 1}]
                </div>
              ))}
            </div>
            <button className="relative px-4 py-2 rounded-full overflow-hidden group/btn bg-white/[0.02] hover:bg-white/[0.05] transition-colors border border-transparent">
              <div className="absolute inset-0 rounded-full border border-primary/30 group-hover/btn:border-primary-container transition-colors"></div>
              <div className="relative flex items-center gap-2 text-sm font-medium text-primary">
                <span className="material-symbols-outlined text-[18px]">account_tree</span>
                View Concept Graph
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
