#!/bin/bash

DATE=$(date +%F-%H-%M)
BACKUP_DIR="/home/ubuntu/backups"

mkdir -p $BACKUP_DIR

# Backup app files
tar -czf $BACKUP_DIR/app-backup-$DATE.tar.gz /home/ubuntu/secure-task-manager

# Backup SQLite database if present
if [ -f /home/ubuntu/secure-task-manager/tasks.db ]; then
    cp /home/ubuntu/secure-task-manager/tasks.db $BACKUP_DIR/tasks-db-$DATE.db
fi

aws s3 cp $BACKUP_DIR/app-backup-$DATE.tar.gz s3://secure-task-backups-amrith/

if [ -f $BACKUP_DIR/tasks-db-$DATE.db ]; then
    aws s3 cp $BACKUP_DIR/tasks-db-$DATE.db s3://secure-task-backups-amrith/
fi

echo "Backup completed at $DATE" >> $BACKUP_DIR/backup.log
