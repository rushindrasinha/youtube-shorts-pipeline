'use client'

import { useEffect, useRef, useState, useCallback } from 'react'

interface AnimatedNumberProps {
  target: number
  duration?: number
  decimals?: number
  prefix?: string
  suffix?: string
  className?: string
}

export function AnimatedNumber({
  target,
  duration = 2000,
  decimals = 0,
  prefix = '',
  suffix = '',
  className,
}: AnimatedNumberProps) {
  const [current, setCurrent] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const hasAnimated = useRef(false)

  const formatNumber = useCallback(
    (n: number) => {
      if (decimals > 0) {
        return n.toFixed(decimals)
      }
      return n.toLocaleString('en-US')
    },
    [decimals]
  )

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated.current) {
          hasAnimated.current = true
          const startTime = performance.now()

          const animate = (now: number) => {
            const elapsed = now - startTime
            const progress = Math.min(elapsed / duration, 1)
            // ease-out cubic
            const eased = 1 - Math.pow(1 - progress, 3)
            setCurrent(eased * target)

            if (progress < 1) {
              requestAnimationFrame(animate)
            } else {
              setCurrent(target)
            }
          }

          requestAnimationFrame(animate)
        }
      },
      { threshold: 0.1 }
    )

    if (ref.current) observer.observe(ref.current)
    return () => observer.disconnect()
  }, [target, duration])

  return (
    <span ref={ref} className={className}>
      {prefix}
      {formatNumber(current)}
      {suffix}
    </span>
  )
}
