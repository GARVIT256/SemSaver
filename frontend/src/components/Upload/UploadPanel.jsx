import React, { useState, useCallback } from 'react';

const UploadPanel = () => {
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [currentFileName, setCurrentFileName] = useState('');

  const onDrop = (e) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files);
    if (droppedFiles.length > 0) {
      handleUpload(droppedFiles[0]);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files.length > 0) {
      handleUpload(e.target.files[0]);
    }
  };

  const handleUpload = async (file) => {
    setIsUploading(true);
    setCurrentFileName(file.name);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append('files', file);

    try {
      // Simulation of progress since simple fetch doesn't support progress events easily
      // In a real app, use XMLHttpRequest or axios for true progress
      const interval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(interval);
            return 90;
          }
          return prev + 10;
        });
      }, 200);

      const response = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });

      clearInterval(interval);
      setUploadProgress(100);

      if (!response.ok) throw new Error('Upload failed');

      const data = await response.json();
      
      setFiles(prev => [
        { 
          name: file.name, 
          size: `${(file.size / (1024 * 1024)).toFixed(1)} MB`, 
          status: 'indexed', 
          progress: 100 
        },
        ...prev
      ]);
    } catch (error) {
      console.error('Upload Error:', error);
      alert('Failed to upload file. Please check if the backend is running.');
    } finally {
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 1000);
    }
  };

  return (
    <div className="flex-1 p-6 lg:p-10 pt-24 max-w-container-max mx-auto w-full">
      <header className="mb-10">
        <h2 className="font-inter text-4xl font-semibold text-on-surface mb-2">Professor Portal</h2>
        <p className="font-body-base text-on-surface-variant max-w-2xl">
          Manage your course materials, monitor AI processing status, and analyze student engagement queries across all your active semesters.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter">
        {/* Upload Zone */}
        <div 
          className="lg:col-span-8 glass-panel rounded-xl p-8 flex flex-col relative overflow-hidden group"
          onDragOver={(e) => e.preventDefault()}
          onDrop={onDrop}
        >
          <div className="absolute top-0 right-0 w-64 h-64 bg-primary-container/5 rounded-full blur-3xl -mr-20 -mt-20"></div>
          <div className="flex justify-between items-center mb-6 z-10">
            <h3 className="text-xl font-semibold text-on-surface flex items-center gap-2">
              <span className="material-symbols-outlined text-primary">cloud_upload</span>
              Knowledge Base Upload
            </h3>
            <span className="text-[12px] font-bold text-primary px-3 py-1 bg-primary/10 rounded-full border border-primary/20 uppercase tracking-wider">
              AI Ingestion Ready
            </span>
          </div>

          <div className="flex-1 border-2 border-dashed border-outline-variant/50 hover:border-primary/50 rounded-lg bg-surface-container-lowest/30 flex flex-col items-center justify-center p-10 transition-colors duration-300 relative z-10 cursor-pointer">
            <input 
              type="file" 
              className="absolute inset-0 opacity-0 cursor-pointer" 
              onChange={handleFileSelect}
              accept=".pdf,.docx,.txt,.pptx"
            />
            <div className="w-16 h-16 rounded-full bg-surface-container flex items-center justify-center mb-4 shadow-[0_0_30px_rgba(166,200,255,0.05)] group-hover:shadow-[0_0_30px_rgba(166,200,255,0.15)] transition-shadow">
              <span className="material-symbols-outlined text-3xl text-on-surface-variant group-hover:text-primary transition-colors">upload_file</span>
            </div>
            <p className="text-xl font-semibold text-on-surface mb-2 text-center">Drag & drop syllabus or reading materials</p>
            <p className="text-sm text-on-surface-variant text-center mb-6">Supports PDF, DOCX, TXT, and PPTX up to 50MB</p>
            <button className="bg-surface-bright hover:bg-surface-container-highest text-on-surface px-6 py-2 rounded-lg border border-outline-variant/30 font-medium transition-colors flex items-center gap-2 pointer-events-none">
              Browse Files
            </button>
          </div>
        </div>

        {/* Processing Queue */}
        <div className="lg:col-span-4 glass-panel rounded-xl p-6 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-semibold text-on-surface">Processing Queue</h3>
          </div>

          <div className="flex flex-col gap-4 overflow-y-auto max-h-[400px] pr-2">
            {isUploading && (
              <div className="bg-surface-container/50 rounded-lg p-4 border border-outline-variant/20 relative overflow-hidden">
                <div className="absolute inset-0 border border-primary/30 rounded-lg shadow-[inset_0_0_10px_rgba(166,200,255,0.1)]"></div>
                <div className="flex justify-between items-start mb-3 relative z-10">
                  <div className="flex items-center gap-3">
                    <span className="material-symbols-outlined text-tertiary">upload</span>
                    <div>
                      <h4 className="text-sm text-on-surface font-medium truncate w-32">{currentFileName}</h4>
                      <p className="font-mono text-[11px] text-on-surface-variant uppercase tracking-widest">
                        {uploadProgress < 100 ? 'Uploading...' : 'Processing...'}
                      </p>
                    </div>
                  </div>
                  <span className="font-mono text-primary text-xs">{uploadProgress}%</span>
                </div>
                <div className="w-full h-1.5 bg-surface-bright rounded-full overflow-hidden relative z-10">
                  <div 
                    className="h-full bg-gradient-to-r from-primary to-secondary-container transition-all duration-300" 
                    style={{ width: `${uploadProgress}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
                  </div>
                </div>
              </div>
            )}

            {files.map((file, idx) => (
              <div key={idx} className="bg-surface-container/30 rounded-lg p-4 border border-outline-variant/10">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]">
                      <span className="material-symbols-outlined text-emerald-400 text-sm">check</span>
                    </div>
                    <div>
                      <h4 className="text-sm text-on-surface font-medium truncate w-32">{file.name}</h4>
                      <p className="font-mono text-on-surface-variant text-[11px] uppercase tracking-widest">Indexed & Searchable</p>
                    </div>
                  </div>
                  <button className="text-on-surface-variant hover:text-on-surface">
                    <span className="material-symbols-outlined text-sm">visibility</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Material Hub Placeholder */}
      <div className="mt-12 opacity-50 grayscale select-none">
        <h3 className="text-2xl font-semibold text-on-surface mb-6">Historical Archives</h3>
        <p className="text-sm text-on-surface-variant">Archived materials from previous semesters will appear here.</p>
      </div>
    </div>
  );
};

export default UploadPanel;
