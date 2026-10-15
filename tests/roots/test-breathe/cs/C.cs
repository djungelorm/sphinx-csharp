using System;

namespace OtherNamespace
{
    public class Foo
    {
        public Foo() {}
    }

    public class Bar
    {
        public Foo Foo;

        public Bar() {
            Foo = new Foo();
        }
    }
}