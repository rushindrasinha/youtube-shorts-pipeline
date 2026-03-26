import Link from 'next/link'

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md space-y-8">
        <div className="text-center">
          <Link href="/" className="font-display text-2xl font-bold">
            Short
            <span className="text-violet-500">Factory</span>
          </Link>
        </div>
        {children}
      </div>
    </div>
  )
}
