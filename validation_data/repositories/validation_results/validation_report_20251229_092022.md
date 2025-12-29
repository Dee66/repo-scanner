# Repository Scanner Validation Report
**Generated:** 2025-12-29T09:20:22.192964

## Executive Summary
- **Total Repositories Analyzed:** 55
- **Successful Analyses:** 45
- **Success Rate:** 81.8%
- **Average Analysis Time:** 2.88 seconds

## Language Coverage
| Language | Total | Successful | Failed | Success Rate |
|----------|-------|------------|--------|--------------|
| python | 8 | 7 | 1 | 87.5% |
| unknown | 15 | 12 | 3 | 80.0% |
| java | 7 | 5 | 2 | 71.4% |
| rust | 6 | 6 | 0 | 100.0% |
| javascript | 8 | 6 | 2 | 75.0% |
| go | 6 | 5 | 1 | 83.3% |
| cpp | 5 | 4 | 1 | 80.0% |

## Repository Type Coverage
| Type | Total | Successful | Failed | Success Rate |
|------|-------|------------|--------|--------------|
| libraries | 28 | 25 | 3 | 89.3% |
| web_apps | 8 | 7 | 1 | 87.5% |
| data_science | 3 | 2 | 1 | 66.7% |
| cli_tools | 8 | 7 | 1 | 87.5% |
| enterprise | 2 | 1 | 1 | 50.0% |
| web_services | 3 | 2 | 1 | 66.7% |
| tools | 2 | 1 | 1 | 50.0% |
| applications | 1 | 0 | 1 | 0.0% |

## Performance Analysis
- **Total Analysis Time:** 158.65 seconds
- **Average per Repository:** 2.88 seconds
- **Fastest Analysis:** 1.04 seconds
- **Slowest Analysis:** 33.98 seconds

## Analysis Failures
- **matplotlib_matplotlib:** analysis exceeded resource limits: CPU limit exceeded: 81.0% > 80%
- **spring-projects_spring-framework:** analysis exceeded resource limits: CPU limit exceeded: 95.0% > 80%
- **apache_camel:** analysis exceeded resource limits: CPU limit exceeded: 84.0% > 80%
- **sharkdp_fd:** analysis exceeded resource limits: CPU limit exceeded: 101.2% > 80%
- **facebook_react:** analysis exceeded resource limits: CPU limit exceeded: 88.0% > 80%
- **vercel_next.js:** analysis exceeded resource limits: CPU limit exceeded: 98.0% > 80%
- **webpack_webpack:** analysis exceeded resource limits: CPU limit exceeded: 81.0% > 80%
- **golang_go:** analysis exceeded resource limits: CPU limit exceeded: 93.0% > 80%
- **kubernetes_kubernetes:** analysis exceeded resource limits: CPU limit exceeded: 96.0% > 80%
- **opencv_opencv:** analysis exceeded resource limits: CPU limit exceeded: 84.0% > 80%

## Success Criteria Assessment
- ❌ FAIL: 100% Analysis Success Rate
- ✅ PASS: All Languages Supported
- ✅ PASS: Reasonable Performance (< 30s avg)