# Priority #4 Trial Report

Generated: 1788062955

## Spine dispatch summary
- Total audit events: 28

### By outcome
- responded: 17
- timeout: 11

## Confirmed command classes
| class | spine ok | spine any | legacy |
|---|---:|---:|---:|
| phone.battery | 7 | 12 | 0 |
| phone.whatsapp.send | 0 | 0 | 0 |
| phone.sms.send | 0 | 0 | 0 |
| phone.app.open | 0 | 0 | 0 |
| phone.notify | 1 | 1 | 0 |
| phone.tts | 0 | 1 | 0 |
| pc.system.lock | 1 | 2 | 0 |
| pc.media.control | 5 | 6 | 0 |

## Automated criteria (partial)
- Command coverage: **False**
- Legacy zero for covered classes: **True**

Planning locus, live declarations, approval gate, kernel independence, and concurrency require live demo attestation — see docs/audits/PRIORITY-4-M11-KEYSTONE-DEMO-CHECKLIST.md
