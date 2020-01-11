submit () {
    if output=$(command sbatch < "$1" 2>&1); then
        echo "$output" | sed -r '1s,^Submitted batch job *([0-9]+).*,\1,'
        return 0
    else
        echo "$output"
        return 1
    fi
}

jobstatus () {
    case $(command squeue --noheader --job "$1" 2>/dev/null | tr -s \  | cut -d\  -f5) in
    '') echo missing ;;
    PD) echo pending ;;
    S|ST) echo suspended ;;
    R) echo running ;;
    CD|CL|F) echo finished ;;
    *) echo unknown ;;
    esac
}

mpirun[openmpi]=mpirun
mpirun[intelmpi]=mpirun
mpirun[mpich]=mpirun

batch_prefix=SBATCH
batch_jobid=%A
batch_name () { echo "--job-name=$1"; }
batch_host () { echo "--nodelist=$1"; }
batch_span () { echo "--nodes=$1"; }
batch_queue () { echo "--partition=$1"; }
batch_cores () { echo "--ntasks=$1"; }
batch_label () { echo "--comment=$1"; }
batch_stdout () { echo "--output=$1"; }
batch_stderr () { echo "--error=$1"; }

environment+=("jobid=\$SLURM_JOB_ID")
environment+=("ncore=\$SLURM_NTASKS")
environment+=("iplist=\$(getent hosts \$SLURM_JOB_NODELIST | cut -d\  -f1 | uniq)")

