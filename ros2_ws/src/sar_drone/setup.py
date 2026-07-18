from setuptools import setup

package_name = 'sar_drone'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/sar_launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Gabrial',
    maintainer_email='gabrialalex2005@gmail.com',
    description='SAR drone agent nodes',
    license='MIT',
    entry_points={
        'console_scripts': [
            'mission_bridge = sar_drone.mission_bridge:main',
            'llm_agent = sar_drone.llm_agent:main',
        ],
    },
)
