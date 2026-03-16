import { Link } from 'react-router-dom';
import { Users, Coins, Clock, Wand2, Image as ImageIcon, Mic, Gamepad2, ArrowRight } from 'lucide-react';

export default function Landing() {
  return (
    <div className="bg-neutral-950 min-h-screen text-neutral-50 font-sans selection:bg-primary-500/30">
      {/* Hero Section */}
      <div className="relative overflow-hidden pt-32 pb-20 lg:pt-48 lg:pb-32">
        <div className="absolute inset-0 opacity-5" style={{ backgroundImage: "radial-gradient(#ffffff 1px, transparent 1px)", backgroundSize: "32px 32px" }}></div>
        <div className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] bg-[radial-gradient(circle_at_center,rgba(79,70,229,0.15)_0,transparent_50%)] pointer-events-none"></div>
        <div className="container mx-auto px-4 relative z-10 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-900/50 border border-primary-500/30 text-primary-300 text-sm font-medium mb-8 shadow-[0_0_15px_-3px_rgba(79,70,229,0.4)]">
            <span className="flex h-2 w-2 rounded-full bg-primary-500 shadow-[0_0_8px_rgba(99,102,241,1)]"></span>
            AIVN Engine v1.0
          </div>
          <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-8">
            From Idea to Playable <br className="hidden md:block" />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-primary-600 drop-shadow-sm">
              Visual Novel
            </span> in Minutes.
          </h1>
          <p className="text-xl md:text-2xl text-neutral-400 max-w-3xl mx-auto mb-12 leading-relaxed">
            The ultimate AI-powered game studio for solo creators. Generate branching stories, detailed characters, dynamic backgrounds, and voice acts effortlessly.
          </p>
          <Link 
            to="/dashboard"
            className="inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-500 text-white px-8 py-4 rounded-xl font-bold text-lg transition-all shadow-[0_0_40px_-10px_rgba(79,70,229,0.5)] hover:shadow-[0_0_60px_-15px_rgba(79,70,229,0.7)] hover:-translate-y-1"
          >
            Enter Studio <ArrowRight size={24} />
          </Link>
        </div>
      </div>

      {/* The Problem */}
      <div className="py-24 bg-neutral-900 border-y border-neutral-800 relative z-20 shadow-xl">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">The Creative Barrier</h2>
            <p className="text-neutral-400 text-lg max-w-2xl mx-auto">Traditional visual novel development is gated by extensive resource requirements, stopping great stories from being told.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            <div className="bg-neutral-950 p-8 rounded-2xl border border-neutral-800 shadow-lg">
              <div className="w-14 h-14 bg-red-900/20 text-red-500 rounded-xl flex items-center justify-center mb-6 border border-red-500/20">
                <Users size={32} />
              </div>
              <h3 className="text-xl font-bold mb-3">Requires a Team</h3>
              <p className="text-neutral-500 leading-relaxed">You typically need dedicated writers, character artists, background illustrators, experienced voice actors, and engine programmers.</p>
            </div>
            <div className="bg-neutral-950 p-8 rounded-2xl border border-neutral-800 shadow-lg">
              <div className="w-14 h-14 bg-red-900/20 text-red-500 rounded-xl flex items-center justify-center mb-6 border border-red-500/20">
                <Coins size={32} />
              </div>
              <h3 className="text-xl font-bold mb-3">Prohibitive Costs</h3>
              <p className="text-neutral-500 leading-relaxed">Commissioning dozens of custom character sprites, distinct expressions, UI elements, and hundreds of voice lines costs thousands of dollars.</p>
            </div>
            <div className="bg-neutral-950 p-8 rounded-2xl border border-neutral-800 shadow-lg">
              <div className="w-14 h-14 bg-red-900/20 text-red-500 rounded-xl flex items-center justify-center mb-6 border border-red-500/20">
                <Clock size={32} />
              </div>
              <h3 className="text-xl font-bold mb-3">Time Consuming</h3>
              <p className="text-neutral-500 leading-relaxed">Directing assets and programming branching narratives takes months or even years of intense labor to fully realize.</p>
            </div>
          </div>
        </div>
      </div>

      {/* The Solution */}
      <div className="py-24 relative z-10">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">Your Personal AI Game Studio</h2>
            <p className="text-neutral-400 text-lg max-w-2xl mx-auto">AIVN automates the arduous production pipeline, allowing you to focus purely on directing your narrative.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="flex gap-6 items-start bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800 hover:border-primary-500/50 transition-colors shadow-md">
              <div className="p-4 bg-primary-900/20 text-primary-400 rounded-xl shrink-0 border border-primary-500/20">
                <Wand2 size={32} />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Automated Story Structuring</h3>
                <p className="text-neutral-400 leading-relaxed">Transform a simple logline into a fully structured screenplay with logical branching paths and detailed scene breakdowns.</p>
              </div>
            </div>
            <div className="flex gap-6 items-start bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800 hover:border-primary-500/50 transition-colors shadow-md">
              <div className="p-4 bg-primary-900/20 text-primary-400 rounded-xl shrink-0 border border-primary-500/20">
                <ImageIcon size={32} />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Instant Art Direction</h3>
                <p className="text-neutral-400 leading-relaxed">Generates character sprites with consistent styles and varied emotional expressions, complete with automatic AI background removal.</p>
              </div>
            </div>
            <div className="flex gap-6 items-start bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800 hover:border-primary-500/50 transition-colors shadow-md">
              <div className="p-4 bg-primary-900/20 text-primary-400 rounded-xl shrink-0 border border-primary-500/20">
                <Mic size={32} />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Expressive Voice Acting</h3>
                <p className="text-neutral-400 leading-relaxed">Brings your distinct cast of characters to life with synthesized voiceovers individually tailored to each character's persona.</p>
              </div>
            </div>
            <div className="flex gap-6 items-start bg-neutral-900/50 p-8 rounded-2xl border border-neutral-800 hover:border-primary-500/50 transition-colors shadow-md">
              <div className="p-4 bg-primary-900/20 text-primary-400 rounded-xl shrink-0 border border-primary-500/20">
                <Gamepad2 size={32} />
              </div>
              <div>
                <h3 className="text-xl font-bold mb-2">Playable Web Client</h3>
                <p className="text-neutral-400 leading-relaxed">Instantly playtest your generated visual novel through our modern, responsive web-based interactive engine without writing code.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Footer CTA */}
      <div className="py-24 bg-gradient-to-t from-primary-900/20 to-transparent relative z-10 border-t border-neutral-800">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-4xl font-bold mb-8">Ready to tell your story?</h2>
          <Link 
            to="/dashboard"
            className="inline-flex items-center gap-2 bg-white text-neutral-950 px-8 py-4 rounded-xl font-bold text-lg hover:bg-neutral-200 transition-colors shadow-lg"
          >
            Open Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}