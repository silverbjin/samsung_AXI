from setuptools import setup
from glob import glob
package_name = 'restaurant_delivery'
setup(name=package_name, version='0.1.0', packages=[package_name],
      data_files=[('share/ament_index/resource_index/packages', ['resource/' + package_name]),
                  ('share/' + package_name, ['package.xml']),
                  ('share/' + package_name + '/config', glob('config/*.yaml'))],
      install_requires=['setuptools'], zip_safe=True,
      maintainer='Restaurant Robot MVP', maintainer_email='noreply@example.invalid',
      description='Independent educational restaurant MVP.', license='Apache-2.0',
      entry_points={'console_scripts': ['delivery_manager = restaurant_delivery.delivery_manager:main']},)
