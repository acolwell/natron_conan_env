#include <iostream>

#include "test_object.h"

TestObject::TestObject() {

}

void TestObject::print() {
	std::cout << "TestObject::print(" << this << ")" << std::endl;
}