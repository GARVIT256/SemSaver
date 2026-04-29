import React, { useState, useRef } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000";

export default function Upload() {
    const [files, setFiles] = useState([]);
    const [dragging, setDragging] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [results, setResults] = useState(null);
    const [error, setError] = useState(null);
    const inputRef = useRef(null);

    const allowedTypes = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
    ];

    const handleDrop = (e) => {
        e.preventDefault();
        setDragging(false);
        const dropped = Array.from(e.dataTransfer.files).filter((f) =>
            allowedTypes.includes(f.type) || f.name.endsWith(".pptx") || f.name.endsWith(".pdf")
        );
        setFiles((prev) => [...prev, ...dropped]);
    };

    const handleFileChange = (e) => {
        setFiles((prev) => [...prev, ...Array.from(e.target.files)]);
    };

    const removeFile = (idx) => {
        setFiles((prev) => prev.filter((_, i) => i !== idx));
    };

    const handleUpload = async () => {
        if (!files.length) return;
        setUploading(true);
        setError(null);
        setResults(null);

        const formData = new FormData();
        files.forEach((f) => formData.append("files", f));

        try {
            const res = await axios.post(`${API_BASE}/upload`, formData, {
                headers: { "Content-Type": "multipart/form-data" },
            });
            setResults(res.data);
            setFiles([]);
        } catch (err) {
            setError(err.response?.data?.detail || "Upload failed. Is the backend running?");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="space-y-6">
            <div>
                <h2 className="text-lg font-semibold text-gray-200 mb-1">Upload Course Materials</h2>
                <p className="text-sm text-gray-500">
                    Supported formats: PDF, PPTX. Files are ingested into the RAG pipeline automatically.
                </p>
            </div>

            {/* Drop zone */}
            <div
                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all ${dragging
                        ? "border-violet-500 bg-violet-900/10"
                        : "border-gray-700 hover:border-gray-500 hover:bg-gray-900"
                    }`}
            >
                <input
                    ref={inputRef}
                    type="file"
                    multiple
                    accept=".pdf,.pptx,.ppt"
                    onChange={handleFileChange}
                    className="hidden"
                />
                <div className="text-4xl mb-3">📁</div>
                <p className="text-gray-300 font-medium">Drop files here or click to browse</p>
                <p className="text-xs text-gray-600 mt-1">PDF, PPTX up to any size</p>
            </div>

            {/* File list */}
            {files.length > 0 && (
                <ul className="space-y-2">
                    {files.map((f, i) => (
                        <li
                            key={i}
                            className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-2.5 text-sm"
                        >
                            <span className="truncate text-gray-300">
                                {f.name.endsWith(".pdf") ? "📄" : "📊"} {f.name}
                                <span className="ml-2 text-gray-600 text-xs">
                                    ({(f.size / 1024).toFixed(1)} KB)
                                </span>
                            </span>
                            <button
                                onClick={() => removeFile(i)}
                                className="ml-4 text-gray-600 hover:text-red-400 transition-colors text-base leading-none"
                            >
                                ✕
                            </button>
                        </li>
                    ))}
                </ul>
            )}

            {/* Upload button */}
            <button
                onClick={handleUpload}
                disabled={!files.length || uploading}
                className={`w-full py-3 rounded-xl font-medium text-sm transition-all ${files.length && !uploading
                        ? "bg-violet-600 hover:bg-violet-500 text-white shadow-lg shadow-violet-900/30"
                        : "bg-gray-800 text-gray-600 cursor-not-allowed"
                    }`}
            >
                {uploading ? (
                    <span className="flex items-center justify-center gap-2">
                        <span className="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                        Ingesting…
                    </span>
                ) : (
                    `Upload & Ingest ${files.length ? `(${files.length} file${files.length > 1 ? "s" : ""})` : ""}`
                )}
            </button>

            {/* Error */}
            {error && (
                <div className="bg-red-900/30 border border-red-800 rounded-lg px-4 py-3 text-sm text-red-300">
                    ⚠ {error}
                </div>
            )}

            {/* Success */}
            {results && (
                <div className="bg-emerald-900/20 border border-emerald-800 rounded-xl px-5 py-4 space-y-3">
                    <p className="font-semibold text-emerald-400 text-sm">✓ {results.message}</p>
                    <div className="space-y-2">
                        {results.summaries.map((s, i) => (
                            <div key={i} className="bg-gray-900 rounded-lg px-4 py-3 text-xs text-gray-400">
                                <span className="font-medium text-gray-200">{s.file}</span>
                                {s.error ? (
                                    <span className="ml-2 text-red-400">Error: {s.error}</span>
                                ) : (
                                    <span className="ml-2">
                                        · {s.chunks} chunks · {s.entities} entities · {s.relations} relations
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}
