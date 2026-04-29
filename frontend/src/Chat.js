import React, { useState, useRef, useEffect } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000";

function Message({ role, content }) {
    const isUser = role === "user";
    return (
        <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser
                        ? "bg-violet-600 text-white rounded-br-sm"
                        : "bg-gray-800 text-gray-200 rounded-bl-sm"
                    }`}
            >
                {content}
            </div>
        </div>
    );
}

function AnswerCard({ data }) {
    return (
        <div className="flex justify-start">
            <div className="max-w-[90%] space-y-3">
                {/* Answer bubble */}
                <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
                    {data.answer}
                </div>

                {/* Metadata row */}
                <div className="flex flex-wrap gap-2 text-xs">
                    {/* Confidence */}
                    <span
                        className={`px-2.5 py-1 rounded-full font-medium ${data.confidence > 0.7
                                ? "bg-emerald-900/40 text-emerald-400"
                                : data.confidence > 0.4
                                    ? "bg-yellow-900/40 text-yellow-400"
                                    : "bg-gray-800 text-gray-500"
                            }`}
                    >
                        Confidence: {(data.confidence * 100).toFixed(1)}%
                    </span>

                    {/* Sources */}
                    {data.sources?.map((s, i) => (
                        <span
                            key={i}
                            className="px-2.5 py-1 rounded-full bg-indigo-900/40 text-indigo-300"
                        >
                            📄 {s}
                        </span>
                    ))}
                </div>

                {/* Graph path */}
                {data.graph_path?.length > 0 && (
                    <div className="bg-violet-900/20 border border-violet-800/50 rounded-xl px-4 py-3 text-xs">
                        <p className="text-violet-400 font-semibold mb-1.5">🔗 Prerequisite Chain</p>
                        <div className="flex flex-wrap items-center gap-1.5">
                            {data.graph_path.map((node, i) => (
                                <React.Fragment key={i}>
                                    <span className="bg-violet-800/40 text-violet-200 px-2 py-0.5 rounded-md">
                                        {node}
                                    </span>
                                    {i < data.graph_path.length - 1 && (
                                        <span className="text-violet-600">→</span>
                                    )}
                                </React.Fragment>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function Chat() {
    const [messages, setMessages] = useState([]);
    const [query, setQuery] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const sendQuery = async () => {
        const q = query.trim();
        if (!q || loading) return;

        setError(null);
        setMessages((prev) => [...prev, { role: "user", text: q }]);
        setQuery("");
        setLoading(true);

        try {
            const res = await axios.post(`${API_BASE}/chat`, { query: q });
            setMessages((prev) => [...prev, { role: "assistant", data: res.data }]);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to get answer. Is the backend running?");
            setMessages((prev) => prev.slice(0, -1)); // remove optimistic user message
            setQuery(q); // restore query
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendQuery();
        }
    };

    return (
        <div className="flex flex-col h-[calc(100vh-11rem)]">
            <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-200 mb-1">Ask About Your Materials</h2>
                <p className="text-sm text-gray-500">
                    Questions are answered strictly from uploaded course content. Add "prerequisite" to trigger graph reasoning.
                </p>
            </div>

            {/* Messages area */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1 mb-4">
                {messages.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
                        <div className="text-5xl opacity-30">💬</div>
                        <p className="text-gray-600 text-sm max-w-xs">
                            Upload your course materials first, then ask questions here.
                        </p>
                        <div className="flex flex-wrap gap-2 justify-center mt-2">
                            {[
                                "What is a neural network?",
                                "What are prerequisites for backpropagation?",
                                "Explain gradient descent",
                            ].map((hint) => (
                                <button
                                    key={hint}
                                    onClick={() => setQuery(hint)}
                                    className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-400 px-3 py-1.5 rounded-full transition-colors"
                                >
                                    {hint}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {messages.map((m, i) =>
                    m.role === "user" ? (
                        <Message key={i} role="user" content={m.text} />
                    ) : (
                        <AnswerCard key={i} data={m.data} />
                    )
                )}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-gray-800 rounded-2xl rounded-bl-sm px-4 py-3 text-sm text-gray-400 flex items-center gap-2">
                            <span className="inline-block w-3 h-3 border-2 border-violet-400 border-t-transparent rounded-full animate-spin" />
                            Thinking…
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Error */}
            {error && (
                <div className="mb-3 bg-red-900/30 border border-red-800 rounded-lg px-4 py-2.5 text-xs text-red-300">
                    ⚠ {error}
                </div>
            )}

            {/* Input */}
            <div className="flex gap-2 items-end bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 focus-within:border-violet-600 transition-colors">
                <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    rows={1}
                    placeholder="Ask a question about your course material…"
                    className="flex-1 bg-transparent text-gray-200 placeholder-gray-600 text-sm resize-none outline-none max-h-40"
                    style={{ minHeight: "1.5rem" }}
                />
                <button
                    onClick={sendQuery}
                    disabled={!query.trim() || loading}
                    className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all ${query.trim() && !loading
                            ? "bg-violet-600 hover:bg-violet-500 text-white"
                            : "bg-gray-800 text-gray-600 cursor-not-allowed"
                        }`}
                >
                    ↑
                </button>
            </div>
            <p className="text-xs text-gray-700 mt-1.5 text-center">
                Enter to send · Shift+Enter for new line
            </p>
        </div>
    );
}
