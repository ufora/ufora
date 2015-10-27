for i in `seq 1 100`;
do
        dd if=/dev/zero of=/mnt/ufora/test$i oflag=direct bs=1M count=1k conv=fdatasync
done
