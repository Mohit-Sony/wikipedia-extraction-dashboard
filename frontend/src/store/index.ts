// src/store/index.ts
import { configureStore } from '@reduxjs/toolkit'
import { api } from './api'
import { uiSlice } from './slices/uiSlice'
import { webSocketSlice } from './slices/webSocketSlice'
import { notificationSlice } from './slices/notificationSlice'

export const store = configureStore({
  reducer: {
    [api.reducerPath]: api.reducer,
    ui: uiSlice.reducer,
    webSocket: webSocketSlice.reducer,
    notifications: notificationSlice.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        ignoredActions: [
          'api/executeQuery/pending',
          'api/executeQuery/fulfilled',
          'api/executeMutation/pending',
          'api/executeMutation/fulfilled',
        ],
      },
    }).concat(api.middleware),
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch