import React from 'react';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-orange-500 mb-4">
          Bybit AI Swing Trader
        </h1>
        <p className="text-xl mb-8">Frontend is working!</p>
        <div className="bg-gray-800 p-6 rounded-lg">
          <p className="text-green-400">✓ React loaded successfully</p>
          <p className="text-green-400">✓ Tailwind CSS working</p>
          <p className="text-yellow-400">⚠ Full UI will load after setup</p>
        </div>
      </div>
    </div>
  );
}