import { ArrowRight, ShoppingCart, Users, TrendingUp } from 'lucide-react';
import { motion } from 'motion/react';
import { toast } from 'sonner';

export function ComingSoon() {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('Спасибо за подписку! Мы сообщим вам об открытии.');
  };

  return (
    <div className="min-h-screen bg-black text-white relative overflow-hidden font-sans selection:bg-lime-400 selection:text-black">
      {/* Background with overlay */}
      <div
        className="absolute inset-0 z-0 opacity-40"
        style={{
          // backgroundImage: `url(${backgroundImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'grayscale(100%) contrast(120%)',
        }}
      />

      {/* Content */}
      <div className="relative z-10 container mx-auto px-4 h-screen flex flex-col justify-center items-center text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          <h1 className="text-6xl md:text-8xl font-black mb-6 tracking-tighter uppercase italic">
            Free<span className="text-lime-400">Sport</span>
          </h1>
        </motion.div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.8 }}
          className="text-xl md:text-2xl text-gray-300 mb-12 max-w-2xl font-light"
        >
          Платформа для профессионалов спорта. Оптовые поставки, экипировка команд и инвентарь
          премиум-класса.
        </motion.p>

        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.8 }}
          onSubmit={handleSubmit}
          className="flex flex-col md:flex-row gap-4 w-full max-w-md"
        >
          <input
            type="email"
            placeholder="Ваш email"
            className="flex-1 px-6 py-4 bg-white/10 backdrop-blur-md border border-white/20 rounded-none focus:outline-none focus:border-lime-400 text-white placeholder-gray-400 transition-colors"
            required
          />
          <button
            type="submit"
            className="px-8 py-4 bg-lime-400 text-black font-bold uppercase tracking-wider hover:bg-lime-300 transition-colors flex items-center justify-center gap-2 group"
          >
            Подписаться
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </button>
        </motion.form>

        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-8 text-left max-w-4xl w-full">
          {[
            {
              icon: ShoppingCart,
              title: 'B2B Платформа',
              desc: 'Удобный кабинет для оптовых заказов',
            },
            {
              icon: Users,
              title: 'Для Команд',
              desc: 'Специальные условия для клубов и федераций',
            },
            {
              icon: TrendingUp,
              title: 'Премиум Бренды',
              desc: 'Только оригинальная продукция мировых лидеров',
            },
          ].map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.9 + index * 0.2, duration: 0.8 }}
              className="p-6 border border-white/10 bg-black/50 backdrop-blur-sm hover:border-lime-400/50 transition-colors group"
            >
              <item.icon className="w-8 h-8 text-lime-400 mb-4 group-hover:scale-110 transition-transform" />
              <h3 className="text-lg font-bold mb-2 uppercase italic">{item.title}</h3>
              <p className="text-gray-400 text-sm">{item.desc}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
