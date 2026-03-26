'use client'

import React from 'react'
import { cn } from '@repo/ui'
import { FadeIn } from './fade-in'

interface StaggerChildrenProps {
  children: React.ReactNode
  className?: string
  staggerMs?: number
  direction?: 'up' | 'down' | 'left' | 'right' | 'none'
}

export function StaggerChildren({
  children,
  className,
  staggerMs = 100,
  direction = 'up',
}: StaggerChildrenProps) {
  return (
    <div className={cn(className)}>
      {React.Children.map(children, (child, index) => (
        <FadeIn delay={index * staggerMs} direction={direction}>
          {child}
        </FadeIn>
      ))}
    </div>
  )
}
