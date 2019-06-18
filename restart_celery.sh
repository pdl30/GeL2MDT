gel2mdt=/var/app/GeL2MDT
docker=/usr/local/bin
$docker/docker-compose -p nt_g2m -f $gel2mdt/docker-compose-prod.yml restart celery
$docker/docker-compose -p nt_g2m -f $gel2mdt/docker-compose-prod.yml restart celery-beat
echo completed: `date`
