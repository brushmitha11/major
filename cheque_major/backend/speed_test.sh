cd /c/Users/Rushmitha/OneDrive/Desktop/cheque
for c in 309062 309067; do
  s=$(date +%s)
  U=$(curl -s -m 300 -F "image=@datasets/raw/idrbt/300/Cheque $c.tif" http://localhost:3000/api/upload)
  ID=$(echo "$U" | python -c "import sys,json; print(json.load(sys.stdin)['upload_id'])")
  curl -s -m 1800 -H "Content-Type: application/json" -d "{\"upload_id\":\"$ID\"}" http://localhost:3000/api/process > cheque_major/backend/speed_$c.json
  echo "$c seconds=$(( $(date +%s) - s ))"
done
echo finished
