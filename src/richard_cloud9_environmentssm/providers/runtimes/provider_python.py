locations = {
    "3.5": '3.5.10',
    "3.6": '3.6.13',
    "3.7": '3.7.10',
    "3.8": '3.8.4',
    "3.9": '3.9.4'
}

def get_build_commands(short_version: str):
    long_version = locations[short_version]
    return [
        f'wget https://www.python.org/ftp/python/{long_version}/Python-{long_version}.tgz',
        'yum -y groupinstall "Development Tools"',
        'yum -y install gcc openssl-devel bzip2-devel libffi-devel',
        f'tar xvf Python-{long_version}.tgz',
        f'cd Python-{long_version}',
        './configure --enable-optimizations --with-ensurepip=install',
        'make -j 8',
        'make altinstall'
]