import { createContext, useContext, useEffect, useState } from 'react'

export type ThemeMode = 'dark' | 'light' | 'system'

interface ThemeContextType {
  theme: ThemeMode
  actualTheme: ThemeMode
  setTheme: (theme: ThemeMode) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined)

export function ThemeProvider({
  children,
  defaultTheme = 'dark',
}: {
  children: React.ReactNode
  defaultTheme?: ThemeMode
}) {
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('theme')
    return (stored as ThemeMode) || defaultTheme
  })

  const [actualTheme, setActualTheme] = useState<ThemeMode>('dark')

  useEffect(() => {
    const root = window.document.documentElement

    // 移除所有主题类
    root.classList.remove('light', 'dark')

    // 确定实际使用的主题
    let effectiveTheme: ThemeMode
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches
        ? 'dark'
        : 'light'
      effectiveTheme = systemTheme
    } else {
      effectiveTheme = theme
    }

    setActualTheme(effectiveTheme)

    // 应用主题
    root.classList.add(effectiveTheme)

    // 设置 CSS 变量
    setCSSVariables(effectiveTheme)

    // 存储偏好
    localStorage.setItem('theme', theme)
  }, [theme])

  // 监听系统主题变化
  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const systemTheme = mediaQuery.matches ? 'dark' : 'light'
      setActualTheme(systemTheme)
      setCSSVariables(systemTheme)
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  return (
    <ThemeContext.Provider value={{ theme, actualTheme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const context = useContext(ThemeContext)
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}

/**
 * 设置 CSS 变量
 */
function setCSSVariables(theme: ThemeMode) {
  const root = document.documentElement

  // 确定实际使用的主题
  let effectiveTheme: 'dark' | 'light' = 'dark'
  if (theme === 'system') {
    effectiveTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  } else {
    effectiveTheme = theme as 'dark' | 'light'
  }

  // 基础颜色
  const colors = {
    dark: {
      '--background': '222.2 84% 4.9%',
      '--foreground': '210 40% 98%',
      '--card': '222.2 84% 4.9%',
      '--card-foreground': '210 40% 98%',
      '--popover': '222.2 84% 4.9%',
      '--popover-foreground': '210 40% 98%',
      '--primary': '217.2 91.2% 59.8%',
      '--primary-foreground': '222.2 47.4% 11.2%',
      '--secondary': '217.2 32.6% 17.5%',
      '--secondary-foreground': '210 40% 98%',
      '--muted': '217.2 32.6% 17.5%',
      '--muted-foreground': '215 20.2% 65.1%',
      '--accent': '217.2 32.6% 17.5%',
      '--accent-foreground': '210 40% 98%',
      '--destructive': '0 62.8% 30.6%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '217.2 32.6% 17.5%',
      '--input': '217.2 32.6% 17.5%',
      '--ring': '224.3 76.3% 48%',
      '--chart-1': '220 70% 50%',
      '--chart-2': '160 60% 45%',
      '--chart-3': '30 80% 55%',
      '--chart-4': '280 65% 60%',
      '--chart-5': '340 75% 55%',
    },
    light: {
      '--background': '210 40% 98%',
      '--foreground': '222.2 84% 4.9%',
      '--card': '0 0% 100%',
      '--card-foreground': '222.2 84% 4.9%',
      '--popover': '0 0% 100%',
      '--popover-foreground': '222.2 84% 4.9%',
      '--primary': '221.2 83.2% 53.3%',
      '--primary-foreground': '210 40% 98%',
      '--secondary': '210 40% 96%',
      '--secondary-foreground': '222.2 47.4% 11.2%',
      '--muted': '210 40% 96%',
      '--muted-foreground': '215.4 16.3% 46.9%',
      '--accent': '210 40% 96%',
      '--accent-foreground': '222.2 47.4% 11.2%',
      '--destructive': '0 84.2% 60.2%',
      '--destructive-foreground': '210 40% 98%',
      '--border': '214.3 31.8% 91.4%',
      '--input': '214.3 31.8% 91.4%',
      '--ring': '221.2 83.2% 53.3%',
      '--chart-1': '12 76% 61%',
      '--chart-2': '173 58% 39%',
      '--chart-3': '197 37% 24%',
      '--chart-4': '43 74% 66%',
      '--chart-5': '27 87% 67%',
    },
  }

  const themeColors = colors[effectiveTheme]

  Object.entries(themeColors).forEach(([key, value]) => {
    root.style.setProperty(key, value)
  })
}
