/* sudo wrapper for hknmod.py

   The website needs to run hknmod to register new officers / committee
   members.
   hknmod.py needs to be run as root.
   Python doesn't respect the setuid bit.

   This program simply forwards its arguments to hknmod.py.
   As a c++ program, its setuid will be respected, and we can have
   www-data run hknmod correctly.

   MAKE SURE PERMISSIONS ARE CORRECT ON THE EXECUTABLE
*/

#include <string>
#include <cstdlib>
#include <iostream>

using namespace std;

int main(int argc, char *argv[])
{
    int i;
    string buf;

    buf += "./hknmod.py ";
    for (i = 1; i < argc; i++) {
        buf += argv[i];
        buf += " ";
    }

    system(buf.c_str());
}
