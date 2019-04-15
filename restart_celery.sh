cd /var/app/GeL2MDT
docker-compose -p nt_g2m -f docker-compose-prod.yml restart celery
docker-compose -p nt_g2m -f docker-compose-prod.yml restart celery-beat
