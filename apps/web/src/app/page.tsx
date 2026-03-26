import { HeroSection } from '@/components/landing/hero-section'
import { PipelineShowcase } from '@/components/landing/pipeline-showcase'
import { FeatureCards } from '@/components/landing/feature-cards'
import { StatsSection } from '@/components/landing/stats-section'
import { PricingSection } from '@/components/landing/pricing-section'
import { CTASection } from '@/components/landing/cta-section'
import { Footer } from '@/components/landing/footer'

export default function Home() {
  return (
    <main>
      <HeroSection />
      <PipelineShowcase />
      <FeatureCards />
      <StatsSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </main>
  )
}
