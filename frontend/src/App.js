import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/Chat/ChatWindow';
import UploadPanel from './components/Upload/UploadPanel';
import AdminDashboard from './components/Dashboard/AdminDashboard';

function App() {
  return (
    <Router>
      <div className="flex bg-surface-container-lowest min-h-screen text-on-surface">
        {/* Ambient Background Lighting */}
        <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
          <div className="absolute top-[-10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-primary/5 blur-[120px]"></div>
          <div className="absolute bottom-[-10%] right-[10%] w-[30vw] h-[30vw] rounded-full bg-secondary-container/10 blur-[100px]"></div>
          <div className="absolute top-[40%] left-[60%] w-[20vw] h-[20vw] rounded-full bg-tertiary-container/5 blur-[80px]"></div>
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:48px_48px] opacity-30"></div>
        </div>

        <Sidebar />
        
        <main className="flex-1 md:ml-[300px] relative z-10 min-h-screen flex flex-col">
          <Routes>
            <Route path="/student" element={<ChatWindow />} />
            <Route path="/professor" element={<UploadPanel />} />
            <Route path="/admin" element={<AdminDashboard />} />
            {/* Default Route */}
            <Route path="/" element={<Navigate to="/student" replace />} />
            <Route path="*" element={<Navigate to="/student" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
