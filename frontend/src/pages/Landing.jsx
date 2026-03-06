import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { Card, CardContent } from '../components/ui/card';
import { LoginForm } from '../components/LoginForm';
import { Truck, Package, MapPin, Users, BarChart3, Shield, Moon, Sun, Check } from 'lucide-react';

export function Landing() {
  const navigate = useNavigate();
  const { isAuthenticated, loading } = useAuth();
  const { theme, toggleTheme } = useTheme();

  useEffect(() => {
    if (!loading && isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [loading, isAuthenticated, navigate]);

  const features = [
    {
      icon: Package,
      title: 'Shipment Tracking',
      description: 'Track every piece with barcode scanning and real-time status updates.'
    },
    {
      icon: Users,
      title: 'Client Management',
      description: 'Manage clients, rates, and payment terms all in one place.'
    },
    {
      icon: Truck,
      title: 'Trip Planning',
      description: 'Organize shipments into trips with automated barcode generation.'
    },
    {
      icon: MapPin,
      title: 'Multi-Destination',
      description: 'Handle complex routes across Africa with ease.'
    },
    {
      icon: BarChart3,
      title: 'Real-time Analytics',
      description: 'Get insights into your operations with comprehensive dashboards.'
    },
    {
      icon: Shield,
      title: 'Multi-Tenant Security',
      description: 'Your data is isolated and secure with subdomain-based tenancy.'
    }
  ];

  const benefits = [
    'Reduce shipment tracking errors by 90%',
    'Speed up warehouse operations with barcode scanning',
    'Manage unlimited clients and shipments',
    'Role-based access for your entire team'
  ];

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#3C3F42' }}>
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50" style={{ backgroundColor: '#3C3F42', borderBottom: '1px solid rgba(232,220,136,0.2)' }}>
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#E8DC88' }}>
              <Truck className="h-5 w-5" style={{ color: '#3C3F42' }} />
            </div>
            <span className="font-heading font-bold text-xl text-white">Servex Holdings</span>
          </div>
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-white/10 text-white"
            data-testid="landing-theme-toggle"
          >
            {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </div>
      </header>

      {/* Hero Section with Login Form */}
      <section className="relative pt-24 pb-16 px-4 overflow-hidden">
        <div className="max-w-7xl mx-auto">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            {/* Left: Info Section */}
            <div className="space-y-8">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-sm border" style={{ backgroundColor: 'rgba(232,220,136,0.15)', borderColor: 'rgba(232,220,136,0.3)', color: '#E8DC88' }}>
                <span className="h-2 w-2 rounded-full animate-pulse" style={{ backgroundColor: '#E8DC88' }} />
                Built for African Freight Companies
              </div>
              
              <h1 className="font-heading text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-white">
                Logistics Management
                <span className="block" style={{ color: '#E8DC88' }}>Made Simple</span>
              </h1>
              
              <p className="text-lg text-white/70 max-w-lg">
                A powerful multi-tenant SaaS platform designed for African freight companies. 
                Track shipments, manage clients, and optimize your operations.
              </p>

              <div className="space-y-3">
                {benefits.map((benefit, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-white/70">
                    <Check className="h-4 w-4 flex-shrink-0" style={{ color: '#E8DC88' }} />
                    {benefit}
                  </div>
                ))}
              </div>

              {/* Stats Card - Desktop Only */}
              <div className="hidden lg:block">
                <Card className="shadow-2xl border-0" style={{ backgroundColor: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(10px)' }}>
                  <CardContent className="p-6">
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="space-y-1">
                          <p className="text-sm text-white/60">Today's Shipments</p>
                          <p className="text-3xl font-bold font-mono text-white">1,247</p>
                        </div>
                        <div className="h-12 w-12 rounded-lg flex items-center justify-center" style={{ backgroundColor: 'rgba(232,220,136,0.2)' }}>
                          <Package className="h-6 w-6" style={{ color: '#E8DC88' }} />
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-4 pt-4" style={{ borderTop: '1px solid rgba(255,255,255,0.1)' }}>
                        <div>
                          <p className="text-xs text-white/50">Warehouse</p>
                          <p className="text-lg font-semibold font-mono text-white">423</p>
                        </div>
                        <div>
                          <p className="text-xs text-white/50">In Transit</p>
                          <p className="text-lg font-semibold font-mono text-white">512</p>
                        </div>
                        <div>
                          <p className="text-xs text-white/50">Delivered</p>
                          <p className="text-lg font-semibold font-mono text-white">312</p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Right: Login Form */}
            <div className="lg:sticky lg:top-24">
              <LoginForm />
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 px-4" style={{ backgroundColor: 'rgba(0,0,0,0.2)' }}>
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="font-heading text-3xl sm:text-4xl font-bold text-white">
              Everything You Need
            </h2>
            <p className="mt-3 text-white/60 max-w-2xl mx-auto">
              A complete logistics management solution built for the unique needs of African freight operations.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <Card key={i} className="group hover:shadow-xl transition-shadow border-0" style={{ backgroundColor: 'rgba(255,255,255,0.07)' }}>
                <CardContent className="p-6">
                  <div className="h-12 w-12 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform" style={{ backgroundColor: 'rgba(232,220,136,0.2)' }}>
                    <feature.icon className="h-6 w-6" style={{ color: '#E8DC88' }} />
                  </div>
                  <h3 className="font-heading font-semibold text-lg mb-2 text-white">{feature.title}</h3>
                  <p className="text-sm text-white/60">{feature.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4" style={{ borderTop: '1px solid rgba(255,255,255,0.1)', backgroundColor: '#3C3F42' }}>
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#E8DC88' }}>
              <Truck className="h-4 w-4" style={{ color: '#3C3F42' }} />
            </div>
            <span className="font-heading font-bold text-white">Servex Holdings</span>
          </div>
          <p className="text-sm text-white/50">
            &copy; {new Date().getFullYear()} Servex Holdings. Built for African businesses.
          </p>
        </div>
      </footer>
    </div>
  );
}
