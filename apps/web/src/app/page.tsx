import { Button } from "@repo/ui";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center">
      <div className="text-center space-y-6">
        <h1 className="font-display text-6xl font-bold tracking-tight">
          Short<span className="bg-gradient-to-r from-violet-500 to-indigo-500 bg-clip-text text-transparent">Factory</span>
        </h1>
        <p className="text-xl text-zinc-400 max-w-md mx-auto">
          Topic in. Short out. Fully automated YouTube Shorts in minutes.
        </p>
        <div className="flex gap-4 justify-center">
          <Button variant="primary" size="lg">Start Free</Button>
          <Button variant="outline" size="lg">See How It Works</Button>
        </div>
      </div>
    </main>
  );
}
