#include "test.h"
#include "GreatObject.h"

class car {
    car() {
        throw 1;
    }
};


bool foo()
{
    return true;
}

void bar()
{
    foo();
    for (int i = 0; i < 10; ++i)
        foo();
}

namespace x {
    void baz() {
        bar()
    }
}

void Moo::method() {
    x::baz();
}


GreatObject::GreatObject()
{



}


void GreatObject::some_method()
{
    auto moo = Moo();
    moo.inline_method();
}


int main()
{
    bar();
    if (foo())
        bar();
}

