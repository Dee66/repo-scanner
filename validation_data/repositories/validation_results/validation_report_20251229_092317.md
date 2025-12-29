# Repository Scanner Validation Report
**Generated:** 2025-12-29T09:23:17.334210

## Executive Summary
- **Total Repositories Analyzed:** 55
- **Successful Analyses:** 42
- **Success Rate:** 76.4%
- **Average Analysis Time:** 2.46 seconds

## Language Coverage
| Language | Total | Successful | Failed | Success Rate |
|----------|-------|------------|--------|--------------|
| python | 8 | 7 | 1 | 87.5% |
| unknown | 15 | 11 | 4 | 73.3% |
| java | 7 | 4 | 3 | 57.1% |
| rust | 6 | 6 | 0 | 100.0% |
| javascript | 8 | 5 | 3 | 62.5% |
| go | 6 | 5 | 1 | 83.3% |
| cpp | 5 | 4 | 1 | 80.0% |

## Repository Type Coverage
| Type | Total | Successful | Failed | Success Rate |
|------|-------|------------|--------|--------------|
| libraries | 28 | 24 | 4 | 85.7% |
| web_apps | 8 | 6 | 2 | 75.0% |
| data_science | 3 | 3 | 0 | 100.0% |
| cli_tools | 8 | 7 | 1 | 87.5% |
| enterprise | 2 | 0 | 2 | 0.0% |
| web_services | 3 | 2 | 1 | 66.7% |
| tools | 2 | 0 | 2 | 0.0% |
| applications | 1 | 0 | 1 | 0.0% |

## Performance Analysis
- **Total Analysis Time:** 135.11 seconds
- **Average per Repository:** 2.46 seconds
- **Fastest Analysis:** 1.03 seconds
- **Slowest Analysis:** 33.37 seconds

## Analysis Failures
- **django_django:** analysis exceeded resource limits: CPU limit exceeded: 99.0% > 80%
- **spring-projects_spring-framework:** analysis exceeded resource limits: CPU limit exceeded: 99.0% > 80%
- **spring-projects_spring-boot:** analysis exceeded resource limits: CPU limit exceeded: 100.0% > 80%
- **wildfly_wildfly:** analysis exceeded resource limits: CPU limit exceeded: 100.0% > 80%
- **apache_camel:** analysis exceeded resource limits: CPU limit exceeded: 99.0% > 80%
- **sharkdp_fd:** analysis exceeded resource limits: CPU limit exceeded: 101.6% > 80%
- **facebook_react:** analysis exceeded resource limits: CPU limit exceeded: 90.9% > 80%
- **vercel_next.js:** analysis exceeded resource limits: CPU limit exceeded: 100.0% > 80%
- **webpack_webpack:** analysis exceeded resource limits: CPU limit exceeded: 99.0% > 80%
- **babel_babel:** analysis exceeded resource limits: CPU limit exceeded: 100.0% > 80%
- **golang_go:** analysis exceeded resource limits: CPU limit exceeded: 99.0% > 80%
- **kubernetes_kubernetes:** analysis exceeded resource limits: CPU limit exceeded: 100.0% > 80%
- **opencv_opencv:** analysis exceeded resource limits: CPU limit exceeded: 98.0% > 80%

## Success Criteria Assessment
- ❌ FAIL: 100% Analysis Success Rate
- ✅ PASS: All Languages Supported
- ✅ PASS: Reasonable Performance (< 30s avg)