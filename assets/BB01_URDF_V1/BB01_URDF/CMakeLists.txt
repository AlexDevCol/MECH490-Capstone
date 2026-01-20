cmake_minimum_required(VERSION 3.8)
project(BB01_URDF)

# find dependencies
find_package(ament_cmake REQUIRED)

foreach(dir config launch meshes urdf)
	install(DIRECTORY ${dir}/
		DESTINATION share/${PROJECT_NAME}/${dir})
endforeach(dir)

ament_package()
