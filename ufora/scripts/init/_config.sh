#   Copyright 2015 Ufora Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

load_config() {
    if [ -f "$UFORA_CONFIG_FILE" ]; then
      # Load the configuration
      . $UFORA_CONFIG_FILE
    fi

    if [ -z $ROOT_DATA_DIR ]; then
      echo "ERROR: ROOT_DATA_DIR has not been specified"
      exit 1
    fi
    if [ ! -d $ROOT_DATA_DIR ]; then
      echo "ERROR: ROOT_DATA_DIR does not exist ($ROOT_DATA_DIR)."
      exit 1
    fi

    if [ -z $UFORA_PID_DIR ]; then
      UFORA_PID_DIR=$ROOT_DATA_DIR/pid
    fi

    if [ -z $UFORA_LOG_DIR ]; then
      UFORA_LOG_DIR=$ROOT_DATA_DIR/logs
    fi

    if [ -z $UFORA_MANAGER_PORT ]; then
      export UFORA_MANAGER_PORT=30002
    fi

    if [ -z $UFORA_GATEWAY_PORT ]; then
      export UFORA_GATEWAY_PORT=30008
    fi

    if [ -z $UFORA_WEB_HTTP_PORT ]; then
      export UFORA_WEB_HTTP_PORT=30000
    fi

    # PORT0, PORT1 are set when running in Apache Marathon
    if [ -z $UFORA_WORKER_CONTROL_PORT ]; then
      export UFORA_WORKER_CONTROL_PORT=${PORT0:-30009}
    fi

    if [ -z $UFORA_WORKER_DATA_PORT ]; then
      export UFORA_WORKER_DATA_PORT=${PORT1:-30010}
    fi

    create_data_dirs
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
    export UFORA_PACKAGE_ROOT=`readlink -m $SCRIPT_DIR/../../..`
    if [[ ! $PYTHONPATH == *"$UFORA_PACKAGE_ROOT"* ]]; then
      export PYTHONPATH="$PYTHONPATH:$UFORA_PACKAGE_ROOT"
    fi
    export UFORA_CONFIG_FILE
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

    FOREVER_DIR=$UFORA_PID_DIR/forever
    FOREVER_ARGS="$FOREVER_ARGS --minUptime 1000 --spinSleepTime 1000 --workingDir $SERVICE_DIR"
    FOREVER_COMMAND="forever $FOREVER_ACTION $FOREVER_ARGS  \
                     -l $UFORA_LOG_DIR/$SERVICE_NAME.log \
                     -p $FOREVER_DIR --pidFile $PID_FILE \
                     -a -c $SERVICE_LAUNCHER $SERVICE_FILE $SERVICE_ARGS"
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
    forever stop -p $FOREVER_DIR $FOREVER_ID
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
    FOREVER_ID=`forever list --plain | $UFORA_PACKAGE_ROOT/ufora/scripts/init/foreverListAndPidToForeverId.py $PID id`
    SERVICE_UPTIME=`forever list --plain | $UFORA_PACKAGE_ROOT/ufora/scripts/init/foreverListAndPidToForeverId.py $PID uptime`
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
