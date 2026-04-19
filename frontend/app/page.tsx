"use client";

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Calendar as CalendarIcon, CheckSquare, Clock, AlertTriangle, MessageSquare, Zap, Loader2, ArrowRight, FileText, Database, Send, Plus, Search, BarChart2, CheckCircle2, Settings, X, ChevronDown } from 'lucide-react';
import Typewriter from 'typewriter-effect';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts';
import ReactMarkdown from 'react-markdown';

// Types exactly matching FastAPI schemas
type PriorityItem = { rank: number; task: string; reason: string; urgency: string; };
type DraftedReply = { subject: string; body: string; to: string; };
type DeadlineAlert = { exists: boolean; event: string; due: string; action_needed: string; };
type RawDataPayload = { emails: any[]; calendar: any[]; drive: any[]; sheets: any | null; };
type AnalysisResponse = { priority_queue: PriorityItem[]; drafted_reply: DraftedReply; deadline_alert: DeadlineAlert; raw_data: RawDataPayload; };
type FocusedItem = { type: 'email' | 'event' | 'sheet' | 'drive', data: any } | null;

const AI_MODELS = [
    {
        group: "Google Gemini",
        models: [
            { id: "gemini/gemini-2.0-flash", name: "Gemini 2.0 Flash" },
            { id: "gemini/gemini-2.0-flash-lite", name: "Gemini 2.0 Flash Lite" },
            { id: "gemini/gemini-2.5-flash-preview-04-17", name: "Gemini 2.5 Flash" },
            { id: "gemini/gemini-2.5-pro-preview-03-25", name: "Gemini 2.5 Pro" },
        ]
    },
    {
        group: "OpenAI",
        models: [
            { id: "openai/gpt-4o", name: "GPT-4o" },
            { id: "openai/gpt-4o-mini", name: "GPT-4o Mini" },
            { id: "openai/gpt-4-turbo", name: "GPT-4 Turbo" },
            { id: "openai/gpt-3.5-turbo", name: "GPT-3.5 Turbo" },
            { id: "openai/gpt-4", name: "GPT-4" },
        ]
    },
    {
        group: "Anthropic",
        models: [
            { id: "anthropic/claude-3-5-sonnet-20240620", name: "Claude 3.5 Sonnet" },
            { id: "anthropic/claude-3-opus-20240229", name: "Claude 3 Opus" },
            { id: "anthropic/claude-3-sonnet-20240229", name: "Claude 3 Sonnet" },
            { id: "anthropic/claude-3-haiku-20240307", name: "Claude 3 Haiku" },
            { id: "anthropic/claude-2.1", name: "Claude 2.1" },
        ]
    },
    {
        group: "xAI",
        models: [
            { id: "xai/grok-beta", name: "Grok Beta" },
            { id: "xai/grok-2-beta", name: "Grok 2 Beta" },
            { id: "xai/grok-vision-beta", name: "Grok Vision" },
        ]
    }
];

export default function Home() {
    const [authStatus, setAuthStatus] = useState<any>(null);
    const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // UI States
    const [activeTab, setActiveTab] = useState<'inbox' | 'calendar' | 'sheets'>('inbox');
    const [focusedItem, setFocusedItem] = useState<FocusedItem>(null);
    const [actionInput, setActionInput] = useState("");
    const [actionLoading, setActionLoading] = useState(false);
    const [actionResult, setActionResult] = useState<{type: string, payload: any} | null>(null);

    // Settings Modal State
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [showProviderDropdown, setShowProviderDropdown] = useState(false);
    const [aiProvider, setAiProvider] = useState("gemini");
    const [apiKeys, setApiKeys] = useState<Record<string, string>>({
        gemini: "", openai: "", anthropic: "", grok: ""
    });

    // Calendar Modal State
    const [showCalModal, setShowCalModal] = useState(false);
    const [calForm, setCalForm] = useState({ title: '', startDate: '', startTime: '', endDate: '', endTime: '' });

    // Fetch auth status & local storage
    useEffect(() => {
        fetch('/auth/status')
            .then(res => res.json())
            .then(data => setAuthStatus(data))
            .catch(console.error);
        
        // Load Settings
        setAiProvider(localStorage.getItem("ops_ai_provider") || "gemini/gemini-2.0-flash");
        try {
            const keys = JSON.parse(localStorage.getItem("ops_api_keys") || "{}");
            setApiKeys(prev => ({...prev, ...keys}));
        } catch (e) {}
    }, []);

    const handleSaveSettings = (e: React.FormEvent) => {
        e.preventDefault();
        localStorage.setItem("ops_ai_provider", aiProvider);
        localStorage.setItem("ops_api_keys", JSON.stringify(apiKeys));
        setShowSettingsModal(false);
    };

    const handleKeyChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const vendor = aiProvider.includes('/') ? aiProvider.split('/')[0] : aiProvider;
        setApiKeys({...apiKeys, [vendor]: e.target.value});
    };

    const handleAnalyze = useCallback(async () => {
        setLoading(true);
        setError(null);
        setAnalysis(null);
        setFocusedItem(null);
        setActionResult(null);
        try {
            const response = await fetch('/api/analyze', { 
                method: 'POST',
                headers: {
                    'x-ai-provider': aiProvider,
                    'x-ai-key': apiKeys[aiProvider.includes('/') ? aiProvider.split('/')[0] : aiProvider] || ''
                }
            });
            if (response.status === 401) {
                setError('Session expired. Please sign in again.');
                setAuthStatus({ is_authenticated: false });
                return;
            }
            if (!response.ok) {
                const errData = await response.json().catch(()=>({}));
                throw new Error(errData.error || "Fetch failed.");
            }
            const data = await response.json();
            setAnalysis(data);
            
            if (data.raw_data?.emails?.length > 0) {
                setFocusedItem({ type: 'email', data: data.raw_data.emails[0] });
            }
        } catch (err: any) {
            setError(err.message || 'Network error.');
        } finally {
            setLoading(false);
        }
    }, [aiProvider, apiKeys]);

    const handleAction = async (actionType: string, overrideContext?: string) => {
        if (!focusedItem) return;
        setActionLoading(true);
        setActionResult(null);
        setError(null);

        try {
            const response = await fetch('/api/action', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'x-ai-provider': aiProvider,
                    'x-ai-key': apiKeys[aiProvider.includes('/') ? aiProvider.split('/')[0] : aiProvider] || ''
                },
                body: JSON.stringify({
                    action_type: actionType,
                    context_item: focusedItem.data,
                    additional_context: overrideContext !== undefined ? overrideContext : actionInput
                })
            });
            const resData = await response.json();
            if (resData.status !== "success") throw new Error(resData.result);
            
            setActionResult({ type: actionType, payload: resData.result });
            if (actionType !== "draft") setActionInput("");
        } catch (err: any) {
            setError(err.message || "Action failed.");
        } finally {
            setActionLoading(false);
        }
    };

    const handleActionSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (focusedItem?.type === 'email') handleAction('draft');
        else if (focusedItem?.type === 'sheet') handleAction('graphify');
        else handleAction('summarize');
    };

    const handleCalSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setShowCalModal(false);
        const explicitTarget = `Schedule this explicitly:
            Title: ${calForm.title}
            Start Date: ${calForm.startDate}
            Start Time: ${calForm.startTime}
            End Date: ${calForm.endDate || 'None'}
            End Time: ${calForm.endTime || 'None'}
        `;
        handleAction('schedule', explicitTarget);
    };

    const copyToClipboard = (text: string) => navigator.clipboard.writeText(text);

    const handleDispatch = async () => {
        if (!actionResult || actionResult.type !== 'draft') return;
        setActionLoading(true);
        setError(null);
        try {
            const response = await fetch('/api/action', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json' ,
                    'x-ai-provider': aiProvider,
                    'x-ai-key': apiKeys[aiProvider.includes('/') ? aiProvider.split('/')[0] : aiProvider] || ''
                },
                body: JSON.stringify({
                    action_type: 'dispatch',
                    context_item: actionResult.payload,
                    additional_context: ''
                })
            });
            const resData = await response.json();
            if (resData.status !== "success") throw new Error(resData.result);
            
            setActionResult({ type: 'dispatch_success', payload: resData.result });
        } catch (err: any) {
            setError(err.message || "Dispatch failed.");
        } finally {
            setActionLoading(false);
        }
    };

    if (!authStatus?.is_authenticated) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center min-h-[90vh] relative overflow-hidden">
                 <motion.div animate={{ y: [0, -20, 0] }} transition={{ repeat: Infinity, duration: 6, ease: "easeInOut" }} className="absolute top-1/4 left-1/4 w-64 h-64 bg-primary/20 rounded-full blur-[100px]" />
                 <motion.div animate={{ y: [0, 20, 0] }} transition={{ repeat: Infinity, duration: 5, ease: "easeInOut" }} className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/10 rounded-full blur-[120px]" />

                <motion.div 
                    initial={{ opacity: 0, scale: 0.9, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} 
                    transition={{ type: "spring", stiffness: 100, damping: 20 }}
                    className="glass-panel p-12 max-w-lg w-full text-center relative z-10 mx-auto shadow-[0_20px_100px_rgba(234,88,12,0.25)] border-primary/20"
                >
                    <div className="w-24 h-24 rounded-3xl mx-auto flex items-center justify-center rotate-3 mb-8 shadow-[0_0_40px_rgba(234,88,12,0.4)] overflow-hidden bg-black/40 border border-white/5">
                        <img src="/logo.png" alt="OpsCore Logo" className="w-full h-full object-cover" />
                    </div>
                    
                    <h1 className="text-5xl font-extrabold tracking-tight mb-4 tracking-tighter text-white">OpsCore</h1>
                    <p className="text-zinc-400 text-lg mb-10 leading-relaxed">Authorize access to Gmail, Calendar, and Drive to build your connected workspace.</p>
                    
                    <a href="/auth/login" className="group relative flex items-center justify-center gap-3 w-full px-8 py-4 text-lg font-bold rounded-2xl bg-white text-black hover:bg-zinc-200 transition-all duration-300">
                        <img src="https://upload.wikimedia.org/wikipedia/commons/c/c1/Google_%22G%22_logo.svg" alt="Google Logo" className="w-6 h-6" />
                        Continue with Google
                        <ArrowRight className="w-5 h-5 opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                    </a>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="flex h-screen overflow-hidden bg-transparent relative">
            
            {/* SETTINGS MODAL */}
            <AnimatePresence>
                {showSettingsModal && (
                    <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
                        <motion.div initial={{scale:0.95}} animate={{scale:1}} exit={{scale:0.95}} className="glass-panel p-8 max-w-lg w-full shadow-[0_0_60px_rgba(255,255,255,0.05)] border-white/10 relative">
                            <button onClick={()=>setShowSettingsModal(false)} className="absolute top-4 right-4 text-zinc-500 hover:text-white"><X className="w-5 h-5"/></button>
                            <h2 className="text-2xl font-bold text-white mb-8 flex items-center gap-3">
                                <Settings className="w-6 h-6 text-zinc-400" /> Settings
                            </h2>
                            
                            <form onSubmit={handleSaveSettings} className="space-y-8">
                                {/* Profile Selection block */}
                                <div className="space-y-3">
                                    <h3 className="text-sm font-semibold tracking-wide text-zinc-400 uppercase border-b border-white/5 pb-2">Profile</h3>
                                    <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/5">
                                        <img src={authStatus.user_picture || "https://upload.wikimedia.org/wikipedia/commons/7/7c/Profile_avatar_placeholder_large.png"} alt="User" className="w-12 h-12 rounded-full border-2 border-white/10" />
                                        <div>
                                            <div className="font-bold text-white">{authStatus.user_name || "Workspace User"}</div>
                                            <div className="text-xs text-zinc-400">{authStatus.user_email || "No email connected"}</div>
                                        </div>
                                    </div>
                                </div>

                                {/* API Integrations */}
                                <div className="space-y-4">
                                    <h3 className="text-sm font-semibold tracking-wide text-zinc-400 uppercase border-b border-white/5 pb-2">Model Integrations</h3>
                                    <div className="relative">
                                        <label className="text-xs font-bold text-zinc-500 uppercase block mb-1">Active Provider</label>
                                        <button 
                                            type="button" 
                                            onClick={() => setShowProviderDropdown(!showProviderDropdown)} 
                                            className="w-full bg-black/40 border border-white/10 rounded-lg p-3 text-white text-sm flex justify-between items-center outline-none transition-all hover:border-primary/50 text-left"
                                        >
                                            {AI_MODELS.flatMap(g => g.models).find(m => m.id === aiProvider)?.name || aiProvider}
                                            <ChevronDown className={`w-4 h-4 text-zinc-400 transition-transform ${showProviderDropdown ? 'rotate-180' : ''}`} />
                                        </button>
                                        
                                        <AnimatePresence>
                                            {showProviderDropdown && (
                                                <motion.div 
                                                    initial={{ opacity: 0, y: -10 }} 
                                                    animate={{ opacity: 1, y: 0 }} 
                                                    exit={{ opacity: 0, y: -10 }} 
                                                    className="absolute z-50 w-full mt-2 bg-black border border-white/10 rounded-xl shadow-2xl max-h-64 overflow-y-auto overflow-x-hidden form-custom-scrollbar shadow-[0_20px_40px_rgba(0,0,0,0.8)]"
                                                >
                                                    {AI_MODELS.map((group, idx) => (
                                                        <div key={idx} className="pb-1">
                                                            <div className="px-3 py-2 text-[10px] font-bold tracking-wider uppercase text-zinc-500 bg-white/5 sticky top-0 backdrop-blur-md z-10">{group.group}</div>
                                                            {group.models.map(model => (
                                                                <button 
                                                                    type="button" 
                                                                    key={model.id} 
                                                                    onClick={() => { setAiProvider(model.id); setShowProviderDropdown(false); }}
                                                                    className={`w-full text-left px-4 py-2.5 text-sm transition-colors flex items-center justify-between ${aiProvider === model.id ? 'bg-primary/20 text-primary font-bold' : 'text-zinc-300 hover:bg-white/10 hover:text-white'}`}
                                                                >
                                                                    {model.name}
                                                                    {aiProvider === model.id && <CheckCircle2 className="w-4 h-4" />}
                                                                </button>
                                                            ))}
                                                        </div>
                                                    ))}
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                    <div>
                                        <label className="text-xs font-bold text-zinc-500 uppercase flex justify-between mb-1">
                                            <span>API Key for {aiProvider.includes('/') ? aiProvider.split('/')[0].toUpperCase() : aiProvider.toUpperCase()}</span>
                                        </label>
                                        <input type="password" value={apiKeys[aiProvider.includes('/') ? aiProvider.split('/')[0] : aiProvider] || ''} onChange={handleKeyChange} className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 text-white text-sm focus:border-primary/50 outline-none transition-all font-mono" placeholder="Set connection string..." />
                                        <p className="text-[10px] text-zinc-500 mt-2">API keys are securely isolated in your browser's local cache and are cleared when you log out.</p>
                                    </div>
                                </div>

                                <div className="flex justify-end gap-3 pt-6 border-t border-white/5">
                                    <button type="button" onClick={() => setShowSettingsModal(false)} className="px-4 py-2.5 rounded-xl text-sm font-semibold text-zinc-400 hover:text-white transition-colors">Close</button>
                                    <button type="submit" className="px-6 py-2.5 rounded-xl bg-white text-black hover:bg-zinc-200 text-sm font-bold shadow-lg transition-all">Save Changes</button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* CALENDAR MODAL OVERLAY */}
            <AnimatePresence>
                {showCalModal && (
                    <motion.div initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} className="fixed inset-0 z-[100] bg-black/60 backdrop-blur-md flex items-center justify-center p-4">
                        <motion.div initial={{scale:0.95}} animate={{scale:1}} exit={{scale:0.95}} className="glass-panel p-8 max-w-md w-full shadow-[0_0_60px_rgba(168,85,247,0.2)] border-purple-500/20">
                            <h2 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-primary bg-clip-text text-transparent mb-6 flex items-center gap-2">
                                <CalendarIcon className="w-6 h-6 text-purple-400" /> Active Scheduling
                            </h2>
                            <form onSubmit={handleCalSubmit} className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-zinc-500 uppercase">Event Title / To Do</label>
                                    <input type="text" value={calForm.title} onChange={e=>setCalForm({...calForm, title: e.target.value})} className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 mt-1 text-white text-sm" placeholder="e.g. Sync Meeting" required />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs font-bold text-zinc-500 uppercase">Start Date</label>
                                        <input type="date" value={calForm.startDate} onChange={e=>setCalForm({...calForm, startDate: e.target.value})} className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 mt-1 text-white text-sm color-scheme-dark" required />
                                    </div>
                                    <div>
                                        <label className="text-xs font-bold text-zinc-500 uppercase">Start Time</label>
                                        <input type="time" value={calForm.startTime} onChange={e=>setCalForm({...calForm, startTime: e.target.value})} className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 mt-1 text-white text-sm color-scheme-dark" required />
                                    </div>
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="text-xs font-bold text-zinc-500 uppercase">End Date (Opt)</label>
                                        <input type="date" value={calForm.endDate} onChange={e=>setCalForm({...calForm, endDate: e.target.value})} className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 mt-1 text-white text-sm color-scheme-dark" />
                                    </div>
                                    <div>
                                        <label className="text-xs font-bold text-zinc-500 uppercase">End Time (Opt)</label>
                                        <input type="time" value={calForm.endTime} onChange={e=>setCalForm({...calForm, endTime: e.target.value})} className="w-full bg-black/40 border border-white/10 rounded-lg p-2.5 mt-1 text-white text-sm color-scheme-dark" />
                                    </div>
                                </div>
                                <div className="flex justify-end gap-3 mt-6 pt-6 border-t border-white/5">
                                    <button type="button" onClick={() => setShowCalModal(false)} className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors">Cancel</button>
                                    <button type="submit" className="px-6 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-xl text-sm font-bold shadow-lg shadow-purple-500/20 transition-colors">Confirm Injection</button>
                                </div>
                            </form>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* VERTICAL MENU SIDEBAR */}
            <div className="w-20 md:w-24 shrink-0 flex flex-col items-center pt-2 pb-8 border-r border-white/5 bg-black/40 backdrop-blur-xl relative z-50 shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
                 <div className="w-12 h-12 bg-black/40 border border-white/10 rounded-2xl flex items-center justify-center shadow-lg shadow-primary/20 mt-0 mb-4 cursor-pointer hover:scale-105 transition-transform overflow-hidden p-1">
                    <img src="/logo.png" alt="Logo" className="w-full h-full object-contain rounded-xl" />
                 </div>
                 
                 <div className="w-full flex flex-col items-center gap-6 mt-4">
                    <button className="w-12 h-12 rounded-xl text-zinc-500 hover:text-white hover:bg-white/5 flex items-center justify-center transition-all group relative">
                        <Database className="w-5 h-5 group-hover:scale-110 transition-transform" />
                        <span className="absolute left-[120%] bg-zinc-800 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">Command Center</span>
                    </button>
                    
                    <button className="w-12 h-12 rounded-xl text-zinc-500 hover:text-white hover:bg-white/5 flex items-center justify-center transition-all group relative">
                        <BarChart2 className="w-5 h-5 group-hover:scale-110 transition-transform" />
                        <span className="absolute left-[120%] bg-zinc-800 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">Analytics</span>
                    </button>
                    
                    <button onClick={() => setShowSettingsModal(true)} className="w-12 h-12 rounded-xl text-zinc-500 hover:text-primary hover:bg-primary/10 flex items-center justify-center transition-all group relative">
                        <Settings className="w-5 h-5 group-hover:scale-110 transition-transform" />
                        <span className="absolute left-[120%] bg-zinc-800 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">Settings</span>
                    </button>
                    
                    <a href="/auth/logout" className="w-12 h-12 rounded-xl text-zinc-500 hover:text-white hover:bg-white/10 flex items-center justify-center transition-all group relative">
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                        <span className="absolute left-[120%] bg-zinc-800 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50">Log Out</span>
                    </a>
                 </div>

                 <div className="mt-auto pointer-events-none">
                    {authStatus?.user_picture && (
                        <div className="w-10 h-10 rounded-full border border-white/10 overflow-hidden shadow-lg opacity-30 mt-auto">
                            <img src={authStatus.user_picture} alt="Avatar" className="w-full h-full object-cover" />
                        </div>
                     )}
                 </div>
            </div>

            <div className="flex-1 flex flex-col overflow-hidden">
                {/* Minimalist Top Nav */}
                <nav className="h-16 flex items-center justify-between px-8 shrink-0 border-b border-white/5">
                    <span className="text-xl font-bold tracking-tight text-white/90">OpsCore Control</span>
                    <div className="flex items-center gap-6">
                        {loading && <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-widest animate-pulse"><Loader2 className="w-4 h-4 animate-spin" /> Deep Syncing...</div>}
                        
                    </div>
                </nav>

                {/* Main App Layout */}
                <div className="flex-1 flex flex-col md:flex-row overflow-hidden p-6 gap-6 max-w-[1700px] mx-auto w-full">
                    
                    {/* LEFT PANEL: Ecosystem Context */}
                    <div className="w-full md:w-[380px] flex flex-col gap-4 shrink-0">
                        <div className="flex items-center justify-between">
                            <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-500">Data Ecosystem</h2>
                            <button
                                onClick={handleAnalyze}
                                disabled={loading}
                                className="flex items-center gap-2 bg-primary/10 text-primary hover:bg-primary/20 px-4 py-1.5 rounded-lg text-sm font-semibold transition-all shadow-[inset_0_0_10px_rgba(234,88,12,0.1)]"
                            >
                                <Search className="w-4 h-4" /> Fetch Global
                            </button>
                        </div>

                        <div className={`glass-panel flex-1 flex flex-col overflow-hidden transition-all duration-500 ${loading ? 'shadow-[inset_0_0_60px_rgba(234,88,12,0.15)] border-primary/30' : ''}`}>
                            {/* Tab Heads */}
                            <div className="flex border-b border-white/5 p-2 gap-2 bg-black/20">
                                {[  { id: 'inbox', icon: Mail, label: 'Inbox' },
                                    { id: 'calendar', icon: CalendarIcon, label: 'Calendar' },
                                    { id: 'sheets', icon: Database, label: 'Drive/Sets' }
                                ].map(tab => (
                                    <button key={tab.id} onClick={() => setActiveTab(tab.id as any)} className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-xl text-sm font-medium transition-all ${activeTab === tab.id ? 'bg-white/10 text-white shadow-sm' : 'text-zinc-500 hover:text-zinc-300 hover:bg-white/5'}`}>
                                        <tab.icon className="w-4 h-4" /> {tab.label}
                                    </button>
                                ))}
                            </div>

                            {/* Tab Body */}
                            <div className="flex-1 overflow-y-auto p-4 space-y-3 relative">
                                {loading && !analysis && (
                                    <div className="absolute inset-0 z-10 bg-black/40 backdrop-blur-sm flex flex-col items-center justify-center text-primary/80">
                                        <Loader2 className="w-10 h-10 animate-spin mb-4" />
                                        <span className="text-sm font-bold uppercase tracking-wider">Syncing Pipelines</span>
                                    </div>
                                )}

                                {!analysis && !loading ? (
                                    <div className="h-full flex flex-col items-center justify-center text-zinc-600 space-y-4">
                                        <Database className="w-12 h-12 opacity-20" />
                                        <p className="text-sm text-center max-w-[200px]">Click "Fetch Global" to ingest massive scale context.</p>
                                    </div>
                                ) : analysis && (
                                    <AnimatePresence mode="popLayout">
                                        {activeTab === 'inbox' && analysis.raw_data.emails.map((email: any, i: number) => (
                                            <motion.button key={i} onClick={() => { setFocusedItem({type: 'email', data: email}); setActionResult(null); }} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className={`w-full text-left p-4 rounded-xl border transition-all ${focusedItem?.data === email ? 'bg-primary/10 border-primary/40 shadow-[inset_0_0_20px_rgba(234,88,12,0.2)]' : 'bg-white/[0.02] border-white/5 hover:bg-white/5'}`}>
                                                <div className="flex justify-between items-start mb-1">
                                                    <span className={`font-semibold truncate text-sm ${focusedItem?.data === email ? 'text-primary' : 'text-white/90'}`}>{email.from.split('<')[0]}</span>
                                                    <span className="text-xs text-zinc-500 ml-2 whitespace-nowrap">{email.date.split(',')[1]?.split(' ')[1] || 'Today'}</span>
                                                </div>
                                                <h4 className="text-sm text-zinc-300 font-medium truncate mb-2">{email.subject}</h4>
                                                <p className="text-xs text-zinc-500 line-clamp-2">{email.snippet}</p>
                                            </motion.button>
                                        ))}

                                        {activeTab === 'calendar' && analysis.raw_data.calendar.map((event: any, i: number) => (
                                            <motion.button key={i} onClick={() => { setFocusedItem({type: 'event', data: event}); setActionResult(null); }} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className={`w-full text-left p-4 rounded-xl border flex items-start gap-4 transition-all ${focusedItem?.data === event ? 'bg-orange-500/10 border-orange-500/40 shadow-[inset_0_0_20px_rgba(249,115,22,0.2)]' : 'bg-white/[0.02] border-white/5 hover:bg-white/5'}`}>
                                                <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex flex-col items-center justify-center text-orange-400 shrink-0">
                                                    <span className="text-[10px] font-bold uppercase">{event.start?.split('T')[0]?.split('-')[1]}</span>
                                                    <span className="text-lg font-bold leading-none">{event.start?.split('T')[0]?.split('-')[2] || 'T'}</span>
                                                </div>
                                                <div>
                                                    <h4 className={`text-sm font-medium mb-1 ${focusedItem?.data === event ? 'text-orange-400' : 'text-white/90'}`}>{event.summary}</h4>
                                                    <div className="text-xs text-zinc-500 flex items-center gap-1"><Clock className="w-3 h-3" /> {event.start?.split('T')[1]?.slice(0,5) || 'All Day'}</div>
                                                </div>
                                            </motion.button>
                                        ))}

                                        {activeTab === 'sheets' && (
                                            <div className="space-y-4">
                                                {analysis.raw_data.sheets && (
                                                    <motion.button onClick={() => { setFocusedItem({type: 'sheet', data: analysis.raw_data.sheets}); setActionResult(null); }} className={`w-full text-left p-4 rounded-xl border transition-all ${focusedItem?.data === analysis.raw_data.sheets ? 'bg-green-500/10 border-green-500/40 shadow-[inset_0_0_20px_rgba(34,197,94,0.2)]' : 'bg-white/[0.02] border-white/5 hover:bg-white/5'}`}>
                                                        <h4 className={`text-sm font-medium mb-3 flex items-center gap-2 ${focusedItem?.data === analysis.raw_data.sheets ? 'text-green-400' : 'text-zinc-300'}`}><Database className="w-4 h-4"/> {analysis.raw_data.sheets.name}</h4>
                                                        <p className="text-xs text-zinc-500 mb-2">Spreadsheet data available for Graphification.</p>
                                                        <div className="overflow-hidden h-[60px] opacity-50"><table className="w-full text-left text-[10px]"><tbody>{analysis.raw_data.sheets.data.slice(0,3).map((row: any, rId: number) => (<tr key={rId} className="border-b border-white/5">{row.slice(0,4).map((cell: any, cId: number) => (<td key={cId} className="p-1 truncate max-w-[60px] text-zinc-400">{cell}</td>))}</tr>))}</tbody></table></div>
                                                    </motion.button>
                                                )}
                                                <h4 className="text-xs font-bold uppercase text-zinc-600 mt-6 mb-2 text-left">Recent Drive Files</h4>
                                                {analysis.raw_data.drive.map((file: any, i: number) => (
                                                    <motion.button key={i} onClick={() => { setFocusedItem({type: 'drive', data: file}); setActionResult(null); }} className={`w-full p-3 rounded-lg border flex items-center gap-3 transition-all ${focusedItem?.data === file ? 'bg-blue-500/10 border-blue-500/40' : 'bg-white/[0.02] border-white/5 hover:bg-white/5'}`}>
                                                        <FileText className="w-4 h-4 text-blue-400" />
                                                        <p className="text-sm text-white/80 truncate flex-1 min-w-0">{file.name}</p>
                                                    </motion.button>
                                                ))}
                                            </div>
                                        )}
                                    </AnimatePresence>
                                )}
                            </div>
                        </div>
                    </div>

                    {/* RIGHT PANEL: Dynamic Action View */}
                    <div className={`flex-1 flex flex-col overflow-hidden relative rounded-3xl pb-2 transition-all duration-700 ${loading ? 'opacity-30 blur-sm scale-95' : 'opacity-100 blur-0 scale-100'}`}>
                        
                        {!focusedItem ? (
                            <div className="flex-1 flex flex-col items-center justify-center glass-panel shadow-[inset_0_0_100px_rgba(0,0,0,0.5)] border-white/5">
                                <div className="w-24 h-24 shadow-[0_0_50px_rgba(234,88,12,0.1)] rounded-3xl border border-white/5 overflow-hidden mb-6 bg-black/40">
                                <img src="/logo.png" alt="Logo" className="w-full h-full object-cover opacity-80" />
                            </div>
                                <h2 className="text-3xl font-extrabold tracking-tighter text-zinc-600 mb-2">Select an Item</h2>
                                <p className="text-zinc-500 text-center max-w-sm">Click on any email, calendar event, or file on the left sidebar to view details and perform actions.</p>
                            </div>
                        ) : (
                            <motion.div key={focusedItem.data.id || focusedItem.data.name || focusedItem.data.subject} initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="flex-1 flex flex-col overflow-hidden">
                                
                                {/* Focus Header */}
                                <div className="mb-6 flex justify-between items-start">
                                    <div>
                                        <div className="flex items-center gap-2 mb-2">
                                            <span className="text-primary font-bold uppercase tracking-wider text-xs bg-primary/10 px-2 py-1 rounded">Isolating: {focusedItem.type}</span>
                                            {actionLoading && <span className="text-zinc-400 text-xs flex items-center gap-1 animate-pulse"><Loader2 className="w-3 h-3 animate-spin"/> Executing AI Routine...</span>}
                                        </div>
                                        <h1 className="text-3xl font-bold tracking-tighter text-white mb-2 line-clamp-1">
                                            {focusedItem.type === 'email' && focusedItem.data.subject}
                                            {focusedItem.type === 'event' && focusedItem.data.summary}
                                            {(focusedItem.type === 'sheet' || focusedItem.type === 'drive') && focusedItem.data.name}
                                        </h1>
                                        <p className="text-zinc-400 text-sm">{focusedItem.type === 'email' ? focusedItem.data.from : 'Data ecosystem detail view.'}</p>
                                    </div>
                                </div>

                                {/* Action Buttons Row */}
                                <div className="flex gap-3 mb-6 flex-wrap pb-6 border-b border-white/5">
                                    <button onClick={() => handleAction('summarize')} className="bg-white/5 hover:bg-white/10 border border-white/10 text-white text-sm font-medium px-4 py-2 rounded-xl flex items-center gap-2 transition-all"><FileText className="w-4 h-4" /> Deep Summarize</button>
                                    {focusedItem.type === 'email' && <button onClick={() => handleAction('draft')} className="bg-primary/20 hover:bg-primary/30 border border-primary/30 text-primary text-sm font-medium px-4 py-2 rounded-xl flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(234,88,12,0.15)]"><MessageSquare className="w-4 h-4" /> Draft Reply</button>}
                                    {focusedItem.type === 'sheet' && <button onClick={() => handleAction('graphify')} className="bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 text-green-400 text-sm font-medium px-4 py-2 rounded-xl flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(34,197,94,0.15)]"><BarChart2 className="w-4 h-4" /> Graphify Data</button>}
                                    <button onClick={() => setShowCalModal(true)} className="bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 text-purple-400 text-sm font-medium px-4 py-2 rounded-xl flex items-center gap-2 transition-all shadow-[0_0_15px_rgba(168,85,247,0.15)]"><CalendarIcon className="w-4 h-4" /> Inject to Calendar</button>
                                </div>

                                {/* Result Display Area */}
                                {error && (
                                    <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex gap-3 text-red-400 text-sm">
                                        <AlertTriangle className="w-5 h-5 flex-shrink-0" /> {error}
                                    </div>
                                )}

                                <div className="flex-1 overflow-y-auto space-y-6 form-custom-scrollbar pr-2">
                                    {/* Raw Data Preview if no action result yet */}
                                    {!actionResult && !actionLoading && focusedItem.type === 'email' && (
                                        <div className="glass-panel p-6 border-white/5 shadow-[inset_0_0_30px_rgba(255,255,255,0.02)]">
                                            <h3 className="text-zinc-500 font-bold text-xs uppercase mb-4">Full Content Readout</h3>
                                            <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">{focusedItem.data.body || focusedItem.data.snippet}</p>
                                        </div>
                                    )}

                                    {/* Graphify Result */}
                                    {actionResult?.type === 'graphify' && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-6 h-[400px]">
                                            <h3 className="text-green-400 font-bold text-xs uppercase tracking-wider mb-6 flex items-center gap-2"><BarChart2 className="w-4 h-4"/> AI Rendered Graph</h3>
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={actionResult.payload}>
                                                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                                    <XAxis dataKey="name" stroke="#888" />
                                                    <YAxis stroke="#888" />
                                                    <Tooltip contentStyle={{ backgroundColor: '#18181b', border: '1px solid #333', borderRadius: '10px' }} />
                                                    <Bar dataKey="value" fill="#22c55e" radius={[4,4,0,0]} />
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </motion.div>
                                    )}

                                    {/* Summarize/Schedule Result with Markdown */}
                                    {(actionResult?.type === 'summarize' || actionResult?.type === 'schedule' || actionResult?.type === 'dispatch_success') && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className={`glass-panel p-6 bg-white/[0.02] border-white/10 ${actionResult.type === 'schedule' ? 'border-purple-500/30 shadow-[inset_0_0_40px_rgba(168,85,247,0.1)]' : (actionResult.type === 'dispatch_success' ? 'border-primary/30 shadow-[inset_0_0_40px_rgba(234,88,12,0.1)]' : '')}`}>
                                            <h3 className="text-zinc-500 font-bold text-xs uppercase tracking-wider mb-4 flex items-center gap-2">
                                                {actionResult.type === 'schedule' ? <><CheckCircle2 className="w-4 h-4 text-purple-400" /> API Injection Success</> : (actionResult.type === 'dispatch_success' ? <><Send className="w-4 h-4 text-primary" /> Active Dispatch Confirmed</> : 'AI Summary')}
                                            </h3>
                                            <div className="text-zinc-300 text-sm leading-relaxed prose prose-invert prose-orange max-w-none prose-sm">
                                                <ReactMarkdown>{actionResult.payload}</ReactMarkdown>
                                            </div>
                                        </motion.div>
                                    )}

                                    {/* Draft Result with Text Editor */}
                                    {actionResult?.type === 'draft' && (
                                        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel flex flex-col overflow-hidden border-primary/20 shadow-[0_0_30px_rgba(234,88,12,0.05)]">
                                            <div className="bg-black/20 p-4 border-b border-primary/20 flex justify-between items-center">
                                                <div className="flex items-center gap-3"><span className="text-xs text-zinc-500">To:</span> <span className="bg-primary/20 text-primary px-3 py-1 rounded-full text-xs font-semibold">{actionResult.payload.to}</span></div>
                                                <div className="flex items-center gap-2">
                                                    <button onClick={() => copyToClipboard(actionResult.payload.body)} className="text-xs text-zinc-400 hover:text-white px-3 py-1 bg-white/5 rounded-lg transition-colors">Copy Output</button>
                                                    <button onClick={handleDispatch} className="text-xs bg-primary hover:bg-orange-500 text-white font-bold px-3 py-1 rounded-lg flex items-center gap-1 transition-colors shadow-lg shadow-primary/20">
                                                        <Send className="w-3 h-3" /> Send Directly
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="p-4 border-b border-white/5 bg-white/[0.02]"><div className="text-xs text-zinc-500 mb-1">Subject</div><div className="text-sm font-semibold text-white">{actionResult.payload.subject}</div></div>
                                            <div className="p-6">
                                                <pre className="font-sans whitespace-pre-wrap text-zinc-300 text-sm leading-relaxed">{actionResult.payload.body}</pre>
                                            </div>
                                        </motion.div>
                                    )}
                                </div>

                                {/* Universal Iteration Prompt */}
                                <div className="mt-4 p-4 glass-panel border-white/10 flex flex-col gap-2 relative shadow-lg shrink-0">
                                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-widest pl-1">Iterate / Modify Action</label>
                                    <form onSubmit={handleActionSubmit} className="flex gap-3 relative z-10">
                                        <input 
                                            type="text" 
                                            value={actionInput}
                                            onChange={e => setActionInput(e.target.value)}
                                            placeholder="e.g. 'Make it more formal', 'Schedule it for tomorrow at 5pm...'"
                                            className="w-full bg-white/5 border border-white/10 rounded-xl py-3 px-4 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-primary/50 transition-colors shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)]"
                                            disabled={actionLoading}
                                        />
                                        <button type="submit" disabled={!actionInput.trim() || actionLoading} className="bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-white rounded-xl px-6 flex items-center justify-center transition-colors">
                                            {actionLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                                        </button>
                                    </form>
                                </div>

                            </motion.div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
