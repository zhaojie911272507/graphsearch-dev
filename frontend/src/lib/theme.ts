/**
 * 前端主题配置
 *
 * 配色方案基于现代深蓝色系，适合数据可视化和长时间使用
 * 支持暗色/亮色模式切换
 */

export const theme = {
  /** 主题色彩 */
  colors: {
    // 主色调 - 蓝色系
    primary: {
      light: '#60A5FA',  // blue-400
      DEFAULT: '#3B82F6', // blue-500
      dark: '#2563EB',    // blue-600
    },

    // 次要色调 - 蓝紫色系
    secondary: {
      light: '#818CF8',   // indigo-400
      DEFAULT: '#6366F1', // indigo-500
      dark: '#4F46E5',    // indigo-600
    },

    // 强调色 - 青色
    accent: {
      light: '#22D3EE',   // cyan-400
      DEFAULT: '#06B6D4', // cyan-500
      dark: '#0891B2',    // cyan-600
    },

    // 成功色
    success: {
      light: '#4ADE80',   // green-400
      DEFAULT: '#22C55E', // green-500
      dark: '#16A34A',    // green-600
    },

    // 警告色
    warning: {
      light: '#FACC15',   // yellow-400
      DEFAULT: '#EAB308', // yellow-500
      dark: '#CA8A04',    // yellow-600
    },

    // 错误色
    error: {
      light: '#F87171',   // red-400
      DEFAULT: '#EF4444', // red-500
      dark: '#DC2626',    // red-600
    },
  },

  /** 暗色主题 */
  dark: {
    background: '#0F172A',      // slate-900
    backgroundSecondary: '#1E293B', // slate-800
    surface: '#1E293B',         // slate-800
    surfaceElevated: '#334155', // slate-700
    border: '#334155',          // slate-700
    text: '#F8FAFC',            // slate-50
    textSecondary: '#94A3B8',   // slate-400
    textMuted: '#64748B',       // slate-500
  },

  /** 亮色主题 */
  light: {
    background: '#F8FAFC',      // slate-50
    backgroundSecondary: '#F1F5F9', // slate-100
    surface: '#FFFFFF',         // white
    surfaceElevated: '#F8FAFC', // slate-50
    border: '#E2E8F0',          // slate-200
    text: '#0F172A',            // slate-900
    textSecondary: '#475569',   // slate-600
    textMuted: '#94A3B8',       // slate-400
  },

  /** 圆角配置 */
  borderRadius: {
    none: '0',
    sm: '0.25rem',
    DEFAULT: '0.375rem',
    md: '0.5rem',
    lg: '0.75rem',
    xl: '1rem',
    '2xl': '1.5rem',
    full: '9999px',
  },

  /** 阴影配置 */
  shadows: {
    none: 'none',
    sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
    md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
    lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
    xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  },

  /** 字体配置 */
  fonts: {
    sans: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    mono: 'JetBrains Mono, "Fira Code", "Cascadia Code", monospace',
  },

  /** 过渡动画 */
  transitions: {
    fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
    normal: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
    slow: '300ms cubic-bezier(0.4, 0, 0.2, 1)',
  },
} as const

export type Theme = typeof theme
