$(echo $(readlink $(which brownie)) | sed 's/\/brownie/\/python/') console_loader.py $1
