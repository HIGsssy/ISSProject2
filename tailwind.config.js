/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './static/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        // Primary theme colors (can be overridden by CSS variables)
        primary: '#3b82f6',
        secondary: '#8b5cf6',
        accent: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
      },
      spacing: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
  // Safelist classes that might be dynamically applied via CSS variables
  // These won't be purged even if not found in templates
  safelist: [
    // Status badges
    'bg-green-600',
    'bg-gray-600',
    'bg-blue-600',
    'bg-purple-600',
    'bg-yellow-50',
    'border-yellow-400',
    'text-white',
    // Dynamic color states
    'hover:bg-opacity-80',
    'focus:ring-2',
    'focus:ring-offset-2',
  ],
  // JIT mode is enabled by default in Tailwind v3+
  // Only generates CSS for classes actually used in templates
  corePlugins: {
    preflight: true,
  },
}
