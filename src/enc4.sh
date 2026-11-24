#!/bin/bash
cd /tmp/vid/out3
M=film_v4_master.mp4
ffmpeg -v error -y -i $M -c:v libx264 -preset fast -crf 21 -maxrate 14M -bufsize 28M -pix_fmt yuv420p -c:a copy -movflags +faststart film_v4_1080.mp4 > e1080.log 2>&1 &
VF="hqdn3d=2.5:2:4:3,scale=720:1280:flags=lanczos"
ffmpeg -v error -y -i $M -vf "$VF" -c:v libx264 -preset slow -b:v 740k -maxrate 1100k -bufsize 1800k -pix_fmt yuv420p -profile:v high -level 4.0 -pass 1 -passlogfile wa4 -an -f null /dev/null > ewa1.log 2>&1
ffmpeg -v error -y -i $M -vf "$VF" -c:v libx264 -preset slow -b:v 740k -maxrate 1100k -bufsize 1800k -pix_fmt yuv420p -profile:v high -level 4.0 -pass 2 -passlogfile wa4 -c:a aac -b:a 96k -ac 2 -movflags +faststart film_v4_whatsapp.mp4 > ewa2.log 2>&1
wait
echo DONE > done_enc4
