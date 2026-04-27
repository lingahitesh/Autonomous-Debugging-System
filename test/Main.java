public class Main
{
    public static void main(String[] args)
    {
        int n = 5;
        while (--n >= 0)
        {
            int result = new Calculator().compute(10);
            System.out.println("Result: " + result);
        }
    }
}