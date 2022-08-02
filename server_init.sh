sudo iptables -t nat -I PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 5401
sudo iptables -t nat -I PREROUTING -p tcp --dport 8080 -j REDIRECT --to-ports 80

screen screen -D -R -S MyCFU
streamlit run MyCFUViz.py --server.port 5401
