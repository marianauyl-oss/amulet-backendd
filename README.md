# Amulet Backend

Flask backend with PostgreSQL & Render deployment support.

## Endpoints
- `/` → Status check
- `/healthz` → Health monitor
- `/check` → Verify license
- `/debit` → Subtract credits
- `/refund` → Add credits
- `/get_voices` → List available voices
- `/admin` → Admin dashboard (Basic Auth)

## Environment Variables
| Key | Description |
|-----|--------------|
| DATABASE_URL | PostgreSQL connection |
| SECRET_KEY | Flask secret |
| ADMIN_USER | Admin login |
| ADMIN_PASS | Admin password |

## Deployment
1. Push to GitHub  
2. Create new Web Service on Render  
3. Add PostgreSQL  
4. Set environment variables  
5. Deploy manually  

✅ Done!