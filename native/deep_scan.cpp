#include <cstddef>
#if defined(_WIN32)
#define CP_EXPORT extern "C" __declspec(dllexport)
#else
#define CP_EXPORT extern "C" __attribute__((visibility("default")))
#endif
CP_EXPORT int cryptopulse_target_scan(const double* closes,const double* highs,std::size_t n,double target_pct,const int* horizons,std::size_t hc,double* frequencies,int* sample_counts){if(!closes||!highs||!horizons||!frequencies||!sample_counts||n<2)return 0;for(std::size_t h=0;h<hc;++h){int horizon=horizons[h];if(horizon<1||n<=static_cast<std::size_t>(horizon)){frequencies[h]=0;sample_counts[h]=0;continue;}std::size_t samples=n-static_cast<std::size_t>(horizon),hits=0;for(std::size_t i=0;i<samples;++i){double threshold=closes[i]*(1.0+target_pct/100.0);bool hit=false;for(std::size_t j=i+1;j<=i+static_cast<std::size_t>(horizon);++j)if(highs[j]>=threshold){hit=true;break;}if(hit)++hits;}frequencies[h]=samples?100.0*static_cast<double>(hits)/static_cast<double>(samples):0.0;sample_counts[h]=static_cast<int>(samples);}return 1;}