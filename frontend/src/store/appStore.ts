import { create } from 'zustand'

interface AppState {
  // UI State
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void

  // Asset Catalog State
  selectedAssetType: string
  setSelectedAssetType: (type: string) => void

  searchQuery: string
  setSearchQuery: (query: string) => void

  // Selected Node
  selectedNodeId: string | null
  setSelectedNodeId: (id: string | null) => void

  // Theme
  darkMode: boolean
  toggleDarkMode: () => void
}

export const useAppStore = create<AppState>((set) => ({
  // UI State
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  // Asset Catalog State
  selectedAssetType: '',
  setSelectedAssetType: (type) => set({ selectedAssetType: type }),

  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  // Selected Node
  selectedNodeId: null,
  setSelectedNodeId: (id) => set({ selectedNodeId: id }),

  // Theme
  darkMode: true,
  toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
}))
