import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import './index.css'

console.log('main.tsx loaded')

// Test: Add a visible element to check if React is rendering
const testDiv = document.createElement('div')
testDiv.textContent = 'React is running - if you see this, main.tsx is working'
testDiv.style.position = 'fixed'
testDiv.style.top = '0'
testDiv.style.left = '0'
testDiv.style.backgroundColor = 'red'
testDiv.style.color = 'white'
testDiv.style.zIndex = '9999'
testDiv.style.padding = '10px'
testDiv.style.fontSize = '16px'
document.body.appendChild(testDiv)

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
