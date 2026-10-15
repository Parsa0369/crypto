// Optional C++17 indicator module. Not yet wired into the Python MVP.
#include <stdexcept>
#include <vector>

namespace cryptopulse {
double rsi14(const std::vector<double>& closes) {
    if (closes.size() < 15) throw std::invalid_argument("RSI needs at least 15 close prices");
    double gains = 0.0, losses = 0.0;
    const auto begin = closes.size() - 14;
    for (std::size_t i = begin; i < closes.size(); ++i) {
        const double delta = closes[i] - closes[i - 1];
        if (delta > 0) gains += delta;
        else losses -= delta;
    }
    gains /= 14.0; losses /= 14.0;
    if (losses == 0.0) return gains > 0.0 ? 100.0 : 50.0;
    return 100.0 - (100.0 / (1.0 + gains / losses));
}
}
