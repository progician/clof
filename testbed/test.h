#pragma once

class Moo {
  int x = 0;
public:
  Moo() = default;

  void method();

  void inline_method() {
    if (x > 3) {
       method();
    }
    else {
      x++;
    }
  }
};
