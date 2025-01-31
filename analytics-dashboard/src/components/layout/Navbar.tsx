// src/components/layout/Navbar.tsx
import React from 'react'
import { Menu } from 'lucide-react'

const Navbar = () => {
  return (
    <header className="fixed top-0 left-0 right-0 h-16 bg-white border-b border-gray-200 z-30">
      <div className="h-full mx-auto px-4">
        <div className="h-full flex items-center justify-between">
          <span className="text-lg font-semibold text-gray-900">
            Analytics Dashboard
          </span>
          <button 
            type="button"
            className="p-1.5 rounded-md text-gray-400 hover:text-gray-500 transition-colors"
          >
            <Menu size={18} />
          </button>
        </div>
      </div>
    </header>
  )
}

export default Navbar