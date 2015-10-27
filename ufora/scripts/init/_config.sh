load_config() {
    if [ -z $BSA_CONFIG_FILE ]; then
      if [ -f $CONFIG_FILE ]; then
        BSA_CONFIG_FILE=$CONFIG_FILE
      else
        echo "ERROR: Cannot find Ufora configuration file. Please set the BSA_CONFIG_FILE environment variable and retry."
        exit 1
      fi
    fi

    # Load the configuration
    . $BSA_CONFIG_FILE

    if [ -z $ROOT_DATA_DIR ]; then
      echo "ERROR: ROOT_DATA_DIR not specified in $BSA_CONFIG_FILE."
      exit 1
    fi
    if [ ! -d $ROOT_DATA_DIR ]; then
      echo "ERROR: ROOT_DATA_DIR specified in $BSA_CONFIG_FILE does not exist ($ROOT_DATA_DIR)."
      exit 1
    fi

    if [ -z $TOKEN_SIGNING_KEY ]; then
      echo "ERROR: TOKEN_SIGNING_KEY not specified in $BSA_CONFIG_FILE."
      exit 1
    fi

    if [ -z $UFORA_SSL_DIR ]; then
      UFORA_SSL_DIR=$ROOT_DATA_DIR/ssl
    fi

    if [ -z $UFORA_PID_DIR ]; then
      echo "WARNING: UFORA_PID_DIR not specified in $BSA_CONFIG_FILE. Defaulting to $ROOT_DATA_DIR/services."
      UFORA_PID_DIR=$ROOT_DATA_DIR/services
    fi

    if [ -z $UFORA_LOG_DIR ]; then
      echo "WARNING: UFORA_LOG_DIR not specified in $BSA_CONFIG_FILE. Defaulting to $ROOT_DATA_DIR/logs"
      UFORA_LOG_DIR=$ROOT_DATA_DIR/logs
    fi

    if [ -z $UFORA_LOCAL_S3_DIR ]; then
      echo "WARNING: UFORA_LOCAL_S3_DIR not specified in $BSA_CONFIG_FILE. Defaulting to $ROOT_DATA_DIR/s3_storage"
      UFORA_LOCAL_S3_DIR=$ROOT_DATA_DIR/s3_storage
    fi

    if [ -z $UFORA_REDIS_DIR ]; then
      echo "WARNING: UFORA_REDIS_DIR not specified in $BSA_CONFIG_FILE. Defaulting to $ROOT_DATA_DIR/redis"
      UFORA_REDIS_DIR=$ROOT_DATA_DIR/redis
    fi

    if [ -z $UFORA_CLUSTER_PORT ]; then
      echo "WARNING: UFORA_CLUSTER_PORT not specified in $BSA_CONFIG_FILE. Defaulting to 30001"
      export UFORA_CLUSTER_PORT=30001
    fi

    if [ -z $UFORA_WEB_HTTP_PORT ]; then
      echo "WARNING: UFORA_WEB_HTTP_PORT not specified in $BSA_CONFIG_FILE. Defaulting to 30000"
      export UFORA_WEB_HTTP_PORT=30000
    fi

    if [ -z $UFORA_WEB_HTTPS_PORT ]; then
      echo "WARNING: UFORA_WEB_HTTPS_PORT not specified in $BSA_CONFIG_FILE. Defaulting to 30005"
      export UFORA_WEB_HTTPS_PORT=30005
    fi

    # PORT0, PORT1 are set when running in Apache Marathon
    if [ -z $UFORA_WORKER_CONTROL_PORT ]; then
      export UFORA_WORKER_CONTROL_PORT=${PORT0:-30009}
    fi

    if [ -z $UFORA_WORKER_DATA_PORT ]; then
      export UFORA_WORKER_DATA_PORT=${PORT1:-30010}
    fi

    UFORA_PACKAGE_DEPENDENCIES_DIR=$UFORA_PACKAGE_ROOT/dependencies
    if [ ! -d $UFORA_PACKAGE_DEPENDENCIES_DIR ]; then
      UFORA_PACKAGE_DEPENDENCIES_DIR=""
    fi
    UFORA_PACKAGE_BIN_DIR=$UFORA_PACKAGE_DEPENDENCIES_DIR/usr/bin
    FOREVER=$UFORA_PACKAGE_BIN_DIR/forever
    if [ "$UFORA_SERVICE_ACCOUNT" != "" ] && [ $UFORA_SERVICE_ACCOUNT != `whoami` ]; then
      RUN_AS_USER="sudo -u $UFORA_SERVICE_ACCOUNT"
    else
      UFORA_SERVICE_ACCOUNT=`whoami`
      RUN_AS_USER=
    fi
}

set_package_root() {
    if [ -d $SCRIPT_DIR/lib ]; then
      UFORA_PACKAGE_ROOT=$SCRIPT_DIR/lib
    else
      UFORA_PACKAGE_ROOT=`readlink -m $SCRIPT_DIR/../../..`
    fi
}

init_config() {
    set_package_root
    if [ -f $CONFIG_FILE ]; then
        # Update the existing configuration file
        update_config_file
    else
        # We don't have a configuration file. Create one.
        create_config_file
    fi

    # Load configuration
    . $CONFIG_FILE
    load_config
}

update_config_file() {
    # update the package root directory
    sed -i s^UFORA_PACKAGE_ROOT=.*^UFORA_PACKAGE_ROOT=$UFORA_PACKAGE_ROOT^g $CONFIG_FILE

}

create_config_file() {
    CONFIG_TEMPLATE=$UFORA_PACKAGE_ROOT/ufora/scripts/init/config.template
    if [ ! -f $CONFIG_TEMPLATE ]; then
        echo "ERROR: Bad Ufora package. Missing config.template."
        exit 1
    fi
    cp $CONFIG_TEMPLATE $CONFIG_FILE
    if [ $? -ne 0 ]; then
        echo "ERROR: Can't copy configuration template to $CONFIG_FILE."
        exit 1
    fi

    echo "UFORA_PACKAGE_ROOT=$UFORA_PACKAGE_ROOT" >> $CONFIG_FILE
    echo "UFORA_SERVICE_ACCOUNT=$UFORA_SERVICE_ACCOUNT" >> $CONFIG_FILE
    echo "ROOT_DATA_DIR=$ROOT_DATA_DIR" >> $CONFIG_FILE
    echo "UFORA_LOG_DIR=$ROOT_DATA_DIR/logs" >> $CONFIG_FILE
    echo "UFORA_PID_DIR=$ROOT_DATA_DIR/services" >> $CONFIG_FILE
    echo "UFORA_BIN_DIR=$ROOT_DATA_DIR/bin" >> $CONFIG_FILE
    echo "UFORA_LOCAL_S3_DIR=$ROOT_DATA_DIR/s3_storage" >> $CONFIG_FILE
    echo "UFORA_REDIS_DIR=$ROOT_DATA_DIR/redis" >> $CONFIG_FILE
    echo "USE_REAL_S3=$USE_REAL_S3" >> $CONFIG_FILE
    echo "USER_DATA_BUCKET=$USER_DATA_BUCKET" >> $CONFIG_FILE
    echo "CUMULUS_TRACK_TCMALLOC=1" >> $CONFIG_FILE

    if [ -z $FORA_MAX_MEM_MB ]; then
      TOTAL_RAM=`free -m | grep Mem | awk '{print $2}'`
      FORA_MAX_MEM_MB=$(( TOTAL_RAM - 1000 ))
    fi
    echo "FORA_MAX_MEM_MB=$FORA_MAX_MEM_MB" >> $CONFIG_FILE

    if [ $FORA_MAX_MEM_MB -gt 7000 ]; then
        echo "EXTERNAL_DATASET_LOADER_SERVICE_THREADS=8" >> $CONFIG_FILE
    fi

    echo "SHARED_STATE_CACHE=$ROOT_DATA_DIR/project_store" >> $CONFIG_FILE
    echo "FORA_LOCAL_DATA_CACHE=$ROOT_DATA_DIR/fora_cache" >> $CONFIG_FILE
    echo "FORA_COMPILER_DUMP_NATIVE_CODE=0" >> $CONFIG_FILE

    if [ ! -z $UFORA_WORKER_CPUS ]; then
      echo "MAX_LOCAL_THREADS=$UFORA_WORKER_CPUS" >> $CONFIG_FILE
    fi

    if [ -z $UFORA_CLUSTER_HOST ]; then
      own_ip_address=`hostname -i`
      if [ $? -eq 0 ]; then
        UFORA_CLUSTER_HOST=`echo $own_ip_address | awk '{print $1}'`
      else
        echo "Unable to determine the local machine's IP address. Please open the configuration file $CONFIG_FILE and set UFORA_CLUSTER_HOST manually."
      fi
    fi
    echo "UFORA_CLUSTER_HOST=$UFORA_CLUSTER_HOST" >> $CONFIG_FILE

}

create_data_dirs() {
  for dir in $UFORA_LOG_DIR $UFORA_PID_DIR $UFORA_BIN_DIR $UFORA_LOCAL_S3_DIR $UFORA_REDIS_DIR $UFORA_SSL_DIR; do
      if [ ! -d $dir ]; then
          mkdir -p $dir
      fi
  done

  if [ ! -d $UFORA_PID_DIR/forever ]; then
      mkdir -p $UFORA_PID_DIR/forever
  fi
}

set_runtime_env() {
    if [[ ! $PATH == *"$UFORA_PACKAGE_BIN_DIR"* ]]; then
      export PATH="$UFORA_PACKAGE_BIN_DIR:$UFORA_PACKAGE_BIN_DIR/../local/bin:$PATH"
    fi
    if [[ ! $PYTHONPATH == *"$UFORA_PACKAGE_ROOT"* ]]; then
      export PYTHONPATH="$PYTHONPATH:$UFORA_PACKAGE_ROOT"
    fi
    export BSA_CONFIG_FILE
    export node=$UFORA_PACKAGE_BIN_DIR/node
}

start_service() {
  echo "Starting $SERVICE_NAME: "
  # The forever process will run as a daemon
  FOREVER_ACTION="start"
  run_with_forever
}

run_service() {
  echo "Running $SERVICE_NAME: "
  # The forever process will continue to run outputting log messages to the console
  FOREVER_ACTION=""
  run_with_forever
}

run_with_forever() {
  if [ "$FOREVER_ID" == "" ]; then
    # Create the pid file, making sure that 
    # the target use has access to them
    touch $PID_FILE
    chown $UFORA_SERVICE_ACCOUNT $PID_FILE

    cd $SERVICE_DIR

    FOREVER_DIR=$UFORA_PID_DIR/forever
    FOREVER_COMMAND="$RUN_AS_USER $FOREVER $FOREVER_ACTION $FOREVER_ARGS --minUptime 1000 --spinSleepTime 1000 -l $UFORA_LOG_DIR/$SERVICE_NAME.log -p $FOREVER_DIR --pidFile $PID_FILE -a -c $SERVICE_LAUNCHER $SERVICE_FILE $SERVICE_ARGS"
    echo $FOREVER_COMMAND
    $FOREVER_COMMAND
    RETVAL=$?
  else
    echo "Instance already running"
    RETVAL=0
  fi
}

stop_service() {
  if [ "$FOREVER_ID" != "" ]; then
    echo -n "Shutting down $SERVICE_NAME:"
    FOREVER_DIR=$UFORA_PID_DIR/forever
    $FOREVER stop -p $FOREVER_DIR $FOREVER_ID
    RETVAL=$?
  else
    echo "$SERVICE_NAME is not running"
    RETVAL=0
  fi
}

service_status() {
  if [ "$FOREVER_ID" != "" ]; then
    echo "Running (forever id: $FOREVER_ID , pid: $PID, uptime: $SERVICE_UPTIME)"
    RETVAL=0
    return
  fi
  echo "Not running"
  RETVAL=-1
}

find_forever_id() {
  if [ -f $PID_FILE ]; then
    read PID < $PID_FILE
  else
    PID=""
  fi

  if [ "$PID" != "" ]; then
    FOREVER_ID=`$RUN_AS_USER $FOREVER list --plain | $UFORA_PACKAGE_ROOT/ufora/scripts/init/foreverListAndPidToForeverId.py $PID id`
    SERVICE_UPTIME=`$RUN_AS_USER $FOREVER list --plain | $UFORA_PACKAGE_ROOT/ufora/scripts/init/foreverListAndPidToForeverId.py $PID uptime`
  fi
}

control_service() {
  PID_FILE=$UFORA_PID_DIR/$SERVICE_NAME.pid
  set_runtime_env
  find_forever_id

  case "$SERVICE_COMMAND" in
    start)
      start_service
      ;;
    run)
      run_service
      ;;
    stop)
      stop_service
      ;;
    status)
      service_status
      ;;
    *)
      echo "Usage: {start|stop|status}"
      RETVAL=1
      ;;
  esac
  exit $RETVAL
}
