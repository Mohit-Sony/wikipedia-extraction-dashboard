// src/hooks/useDebounce.ts
import { useState, useEffect } from 'react'

/**
 * Custom hook that debounces a value by delaying updates until after a specified delay
 * 
 * @param value - The value to debounce
 * @param delay - The delay in milliseconds
 * @returns The debounced value
 * 
 * @example
 * const [searchTerm, setSearchTerm] = useState('')
 * const debouncedSearchTerm = useDebounce(searchTerm, 300)
 * 
 * // API call will only trigger 300ms after user stops typing
 * useEffect(() => {
 *   if (debouncedSearchTerm) {
 *     // Make API call
 *   }
 * }, [debouncedSearchTerm])
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    // Set up a timer to update the debounced value after the delay
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    // Clear the timeout if value changes before delay completes
    // This is the key to the debouncing behavior
    return () => {
      clearTimeout(handler)
    }
  }, [value, delay]) // Re-run effect when value or delay changes

  return debouncedValue
}