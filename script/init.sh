imgName=antani_fat
APP_DIR="app"
SERVER=10.0.49.178
PORT="5000-5010"
# generate requirements file
pip freeze --target > requirements.txt
grep import $(find . -name "*.py") | cut -d ":" -f2 > requirements.txt
awk '$1 ~ /from/ { print $2 }' requirements.txt > tmp.txt
awk '$1 !~ /from/ { print  $2}' requirements.txt >> tmp.txt
cut -d "." -f1 tmp.txt | cut -d "," -f1 | sort | uniq > requirements.txt
rm tmp.txt
#create dockerfile
echo "FROM python:3.6
WORKDIR /$APP_DIR
COPY requirements.txt ./
RUN ls
RUN apt-get update
RUN apt -y install vim libspatialindex-dev cmake redis redis-server
RUN pip install -r requirements.txt
ENV LAV_DIR=/$APP_DIR/
EXPOSE $PORT
CMD [ \"bash\", \"src/antani/server.sh\" ]" > Dockerfile
#apache
chmod u+x apache.sh
./apache.sh
#host start docker
sudo service docker start
sudo usermod -a -G docker $USER
#host start/setup container
docker build -t $imgName .
docker pull redis
docker run -d --name redis1 redis
docker run -it --link redis1:redis --name $imgName -p $PORT:$PORT -v $(pwd):/$APP_DIR $imgName bash
#run prod
docker run --name $imgName -v $(pwd):/app --rm -it -p $PORT:$PORT -p $imgName
docker exec -it $imgName python src/antani/backend.py
#firewall
sudo yum install httpd nmap -y
sudo yum -y install ufw
sudo amazon-linux-extras install epel
sudo service httpd start
nc -zv $SERVER $PORT
